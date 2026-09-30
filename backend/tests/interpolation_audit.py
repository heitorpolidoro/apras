"""A static audit of every f-string interpolation in an HTML-rendering module.

APRAS-117. ``project_report_service`` builds its document with f-strings, so
the only thing between a contractor-supplied string and a public page is the
``_e()`` call at the interpolation. A hand-written list of the call sites that
*ought* to escape goes stale the first time someone adds a field -- the new
one is simply absent from the list and nothing fails -- so this module derives
the inventory from the source instead.

**What it decides.** For each interpolation it answers one question: *can the
value be text that came from storage?* Three verdicts:

``ESCAPED``
    the interpolated expression is a call to the module's escaper.
``SAFE``
    the value provably cannot carry ``<``, ``&`` or a quote from storage --
    a number under a numeric format spec, a date component, a module-scope
    constant (module bodies run at import, where no stored value exists), a
    fragment already assembled by an audited f-string, or the return of a
    module function whose every return is itself one of these.
``RAW``
    anything else. Every ``RAW`` verdict is a finding: either a real escaping
    hole or a value that is safe for a reason this module cannot see, in which
    case the reason is declared at the call site of :func:`audit` *and* pinned
    by a runtime test.

**Soundness direction matters.** The analysis is deliberately pessimistic:
attribute access, subscripting an unknown value, ``str()``, ``getattr()`` and
any call it cannot resolve are all ``RAW``. A rule that is too strict costs a
declared exemption and a test; a rule that is too loose costs the injection
this audit exists to prevent, silently. Where the two were in tension the
strict side was taken -- which is why ``_stylesheet`` reports ``RAW`` even
though ``app.core.branding`` validates its palette into ``oklch(...)``.

The parameter analysis is intraprocedural-plus-call-sites: a module-private
function's parameter is safe only when *every* call site inside the module
passes a safe argument, and a public function's parameters are always ``RAW``
because callers outside the module are not visible here. Both directions of
that rule are pessimistic.

**What it does not track**, so that nobody reads the paragraph above as a
guarantee it is not:

* **subscript and attribute assignment targets.** ``parts[0] = stored`` and
  ``obj.field = stored`` bind nothing this analysis sees, so a container
  proven safe stays safe after one;
* **cross-function mutation.** A callee appending to a list its caller passed
  in is invisible; only ``name.append(...)`` inside the same function binds;
* **``**payload`` call sites.** :meth:`_Audit._callsites` maps arguments to
  parameters by position and by keyword name, so a call that splats a mapping
  contributes nothing and the parameter is judged on the other call sites
  alone;
* **module-scope containers written at runtime.** A module-level ``dict``
  filled by subscript after import is still treated as import-time data;
* **``strftime``/``isoformat`` on a non-date receiver.** They are safe by
  method name, not by the receiver's type.

Each needs contorted code that this module does not contain, which is why they
are recorded rather than fixed -- but every one of them is a way to reach
``SAFE`` with a stored string, and a future renderer written in any of those
shapes gets no protection from this file.
"""

from __future__ import annotations

import ast
import copy
from collections import defaultdict
from dataclasses import dataclass

#: The module's escaper. A call to it is what ``ESCAPED`` means.
ESCAPER = "_e"

#: Builtins whose result cannot be storage text **whatever they are given**:
#: numeric coercions and sizes. ``str`` is not here -- ``str(stored)`` is
#: exactly the hole -- and neither are ``max``/``min``/``sorted``, which are
#: :data:`ELEMENT_SELECTORS` below.
SAFE_CALLABLES = frozenset(
    {"len", "float", "int", "abs", "round", "sum", "bool", "Decimal"}
)

#: Builtins that **return one of their arguments**, or a rearrangement of
#: them, rather than converting anything: over stored text they answer stored
#: text. ``max(update.created_at for update in updates)`` is a real line of the
#: audited module, so ``f"{max(u.title for u in updates)}"`` is one edit away
#: -- and while these three sat in :data:`SAFE_CALLABLES` it audited ``SAFE``.
#: They are routed through the composite rule instead: safe exactly when every
#: argument is.
ELEMENT_SELECTORS = frozenset({"max", "min", "sorted"})

#: Methods safe on any receiver. ``strftime``/``isoformat`` answer a date
#: stamp; ``join`` is handled separately because its safety is its arguments'.
SAFE_METHODS = frozenset({"strftime", "isoformat"})

#: ``str`` methods that answer a rearrangement of their receiver and their
#: arguments. Safe only when **both** are -- ``"".join`` and ``replace`` can
#: each introduce a ``<`` that came from one of them.
SAFE_TRANSFORMS = frozenset(
    {"join", "replace", "strip", "lstrip", "rstrip", "upper", "lower", "capitalize"}
)

#: Methods that put a value **into** a local container. Without these,
#: ``cased: list[str] = []`` followed by ``cased.append(stored)`` would read
#: as a safe empty list -- and that is exactly how ``title_case`` builds its
#: result.
MUTATORS = frozenset({"append", "extend", "insert", "add", "update"})

#: Annotations whose values are not text at all, so interpolating one -- or a
#: component of one, such as ``today.year`` -- cannot carry markup.
NON_TEXT_ANNOTATIONS = frozenset(
    {
        "int",
        "float",
        "bool",
        "Decimal",
        "date",
        "datetime",
        "_dt.date",
        "_dt.datetime",
        "UUID",
    }
)

#: Presentation types that force a numeric rendering. ``{x:02d}`` and
#: ``{x:,.2f}`` cannot emit ``<`` whatever ``x`` is; ``{x:s}`` and ``{x}`` can.
NUMERIC_PRESENTATIONS = frozenset("bcdeEfFgGnoxX%")

ESCAPED = "escaped"
SAFE = "safe"
RAW = "raw"


@dataclass(frozen=True)
class Interpolation:
    """One ``{...}`` of one f-string, with the verdict and why."""

    function: str
    lineno: int
    expression: str
    verdict: str
    reason: str

    @property
    def site(self) -> str:
        """The key a declared exemption is written against."""
        return f"{self.function}:{self.expression}"

    def __str__(self) -> str:  # pragma: no cover - failure messages only
        return f"line {self.lineno} in {self.function}(): {{{self.expression}}}"


class _Audit:
    """The analysis over one parsed module."""

    def __init__(self, tree: ast.Module) -> None:
        self.tree = tree
        self.functions: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {
            node.name: node
            for node in tree.body
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        }
        self.module_names = self._module_scope_names()
        self.annotations = {
            name: self._annotations(fn) for name, fn in self.functions.items()
        }
        self.bindings = {
            name: self._bindings(fn) for name, fn in self.functions.items()
        }
        self.callsites = self._callsites()
        self._resolving: set[tuple[str, str]] = set()
        # Greatest fixpoint: start optimistic, only ever demote. Recursion and
        # accumulator rebinding (``cards += f"..."``) both terminate this way.
        self.returns_safe = dict.fromkeys(self.functions, True)
        self.param_safe = {
            (name, param): True
            for name, fn in self.functions.items()
            for param in _params(fn)
        }
        self._fixpoint()

    # -- inventory ---------------------------------------------------------

    def _module_scope_names(self) -> set[str]:
        """Every name bound at module scope, plus the imported ones.

        A module body runs at import, before any request and any database
        session, so nothing it binds can hold a stored string.
        """
        names: set[str] = set()
        for node in self.tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    names.update(_target_names(target))
            elif isinstance(node, ast.AnnAssign):
                names.update(_target_names(node.target))
            elif isinstance(node, ast.Import | ast.ImportFrom):
                names.update(
                    alias.asname or alias.name.split(".")[0] for alias in node.names
                )
            elif isinstance(node, ast.If | ast.Try):
                for inner in ast.walk(node):
                    if isinstance(inner, ast.Import | ast.ImportFrom):
                        names.update(
                            alias.asname or alias.name.split(".")[0]
                            for alias in inner.names
                        )
        return names

    @staticmethod
    def _annotations(
        fn: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> dict[str, frozenset[str]]:
        out: dict[str, frozenset[str]] = {}
        for arg in _args(fn):
            if arg.annotation is not None:
                out[arg.arg] = _annotation_types(arg.annotation)
        for node in ast.walk(fn):
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                out[node.target.id] = _annotation_types(node.annotation)
        return out

    def _bindings(
        self, fn: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> dict[str, list[ast.expr]]:
        """Local name -> every expression it can hold."""
        out: dict[str, list[ast.expr]] = defaultdict(list)
        for node in ast.walk(fn):
            for name, value in _binding_pairs(node):
                out[name].append(value)
        return out

    def _callsites(self) -> dict[tuple[str, str], list[tuple[str, ast.expr]]]:
        """``(callee, parameter)`` -> every ``(calling function, argument)``."""
        out: dict[tuple[str, str], list[tuple[str, ast.expr]]] = defaultdict(list)
        for caller, fn in self.functions.items():
            for node in ast.walk(fn):
                if not isinstance(node, ast.Call) or not isinstance(
                    node.func, ast.Name
                ):
                    continue
                callee = self.functions.get(node.func.id)
                if callee is None:
                    continue
                params = _params(callee)
                for index, arg in enumerate(node.args):
                    if index < len(params):
                        out[(node.func.id, params[index])].append((caller, arg))
                for keyword in node.keywords:
                    if keyword.arg:
                        out[(node.func.id, keyword.arg)].append((caller, keyword.value))
        return out

    def _fixpoint(self) -> None:
        changed = True
        while changed:
            changed = False
            for name, fn in self.functions.items():
                for param in _params(fn):
                    if self.param_safe[(name, param)] and not self._param_holds(
                        name, param
                    ):
                        self.param_safe[(name, param)] = False
                        changed = True
                if not self.returns_safe[name]:
                    continue
                if not self._returns_hold(fn, name):
                    self.returns_safe[name] = False
                    changed = True

    def _returns_hold(
        self, fn: ast.FunctionDef | ast.AsyncFunctionDef, name: str
    ) -> bool:
        """Is every value ``fn`` can hand back safe?

        **A generator is never safe.** It has no ``ast.Return`` carrying the
        values it produces, so ``all()`` over its (empty) return list is
        vacuously true -- and a helper that yielded ``milestone.title``, joined
        into the document by ``", ".join(...)``, audited ``SAFE``. Vacuous
        truth is not "every return is safe", which is what the verdict claims,
        so a ``yield`` anywhere in the body demotes the function outright.
        """
        if any(isinstance(node, ast.Yield | ast.YieldFrom) for node in ast.walk(fn)):
            return False
        returns = [
            node.value
            for node in ast.walk(fn)
            if isinstance(node, ast.Return) and node.value is not None
        ]
        return all(self.is_safe(value, name) for value in returns)

    def _param_holds(self, function: str, param: str) -> bool:
        if _is_non_text(self.annotations[function].get(param)):
            return True
        if not function.startswith("_"):
            # Public entry point: its callers are outside this module.
            return False
        sites = self.callsites.get((function, param))
        if not sites:
            return False
        return all(self.is_safe(arg, caller) for caller, arg in sites)

    # -- the rules ---------------------------------------------------------

    def is_safe(self, node: ast.expr, scope: str) -> bool:
        """Can ``node`` never evaluate to storage text, in ``scope``?

        One ordered dispatch over the node kinds, so the answer for an
        expression the analysis has no rule for is the pessimistic ``False``
        rather than an accident of where a branch fell.
        """
        for node_types, rule in _RULES:
            if isinstance(node, node_types):
                return rule(self, node, scope)
        return False

    def _always_safe(self, node: ast.expr, scope: str) -> bool:
        """A literal, or a comparison, which renders as ``True``/``False``."""
        return True

    def _joined_safe(self, node: ast.expr, scope: str) -> bool:
        if isinstance(node, ast.FormattedValue):
            return _numeric_format(node.format_spec) or self.is_safe(node.value, scope)
        assert isinstance(node, ast.JoinedStr)
        return all(
            self._joined_safe(value, scope)
            for value in node.values
            if isinstance(value, ast.FormattedValue)
        )

    def _composite_safe(self, node: ast.expr, scope: str) -> bool:
        """Every sub-expression that can reach the output has to be safe."""
        return all(self.is_safe(child, scope) for child in _operands(node))

    def _subscript_safe(self, node: ast.expr, scope: str) -> bool:
        assert isinstance(node, ast.Subscript)
        return self.is_safe(node.value, scope)

    def _attribute_safe(self, node: ast.expr, scope: str) -> bool:
        """A component of a date or a number is not text; a dot into anything
        else is a model field until proven otherwise."""
        assert isinstance(node, ast.Attribute)
        return isinstance(node.value, ast.Name) and _is_non_text(
            self.annotations.get(scope, {}).get(node.value.id)
        )

    def _call_safe(self, node: ast.expr, scope: str) -> bool:
        assert isinstance(node, ast.Call)
        func = node.func
        if isinstance(func, ast.Name):
            if func.id in ELEMENT_SELECTORS:
                return self._arguments_safe(node, scope, node.args)
            return (
                func.id == ESCAPER
                or func.id in SAFE_CALLABLES
                or (func.id in self.functions and self.returns_safe[func.id])
            )
        if isinstance(func, ast.Attribute):
            return self._method_safe(node, func, scope)
        return False

    def _method_safe(self, node: ast.Call, func: ast.Attribute, scope: str) -> bool:
        if func.attr in SAFE_METHODS:
            return True
        if func.attr in SAFE_TRANSFORMS:
            # A rearrangement of the receiver and the arguments, so it is safe
            # exactly when both are.
            return self.is_safe(func.value, scope) and self._arguments_safe(
                node, scope, node.args
            )
        if func.attr == "get":
            # A lookup in a safe mapping answers a safe value, or the default.
            return self.is_safe(func.value, scope) and self._arguments_safe(
                node, scope, node.args[1:]
            )
        return False

    def _arguments_safe(
        self, node: ast.Call, scope: str, positional: list[ast.expr]
    ) -> bool:
        """``positional`` **and every keyword**.

        No ``str`` method this module calls takes a keyword, so leaving them
        out was latent rather than live -- but "the analysis did not look" is
        how the two false-``SAFE`` shapes ER7 records got in, and a keyword is
        an argument.
        """
        return all(self.is_safe(arg, scope) for arg in positional) and all(
            self.is_safe(keyword.value, scope) for keyword in node.keywords
        )

    def _name_lookup(self, node: ast.expr, scope: str) -> bool:
        assert isinstance(node, ast.Name)
        return self._name_safe(node.id, scope)

    def _name_safe(self, name: str, scope: str) -> bool:
        """**Local scope first.** Python resolves a name to the local binding
        whichever module-scope name it shadows, and so must this: a local
        called ``html``, ``json``, ``date``, ``clock`` or any of the module's
        own function names would otherwise read as safe whatever it holds --
        ``html = project.description`` followed by ``f"<p>{html}</p>"`` was
        ``SAFE`` while this method tested :attr:`module_names` first.

        **A parameter is judged on its call sites *and* on every rebinding.**
        Returning on ``param_safe`` alone made the ordinary ``or``-default
        form invisible -- ``label = label or project.description`` audited
        ``SAFE``, because the short-circuit returned before :attr:`bindings`
        was consulted even though ``_bindings`` had already collected the
        rebinding.
        """
        bindings = self.bindings.get(scope, {}).get(name)
        fn = self.functions.get(scope)
        if fn is not None and name in _params(fn):
            if not self.param_safe[(scope, name)]:
                return False
            return not bindings or self._bindings_safe(name, scope, bindings)
        if bindings:
            return self._bindings_safe(name, scope, bindings)
        if _is_non_text(self.annotations.get(scope, {}).get(name)):
            return True
        # Not bound in this function, so it resolves to module scope: a module
        # body runs at import, where no stored value exists.
        return name in self.module_names or name in self.functions

    def _bindings_safe(self, name: str, scope: str, bindings: list[ast.expr]) -> bool:
        """Every expression the local can hold has to be safe.

        Checked **before** the name's annotation, not after: an annotation is
        the author's claim about the value and the binding is the value, so a
        local annotated ``str`` -- or ``int`` -- that is assigned a model field
        is unsafe whatever its annotation says.
        """
        key = (scope, name)
        if key in self._resolving:
            return True  # broken cycle; the other binding still decides
        self._resolving.add(key)
        try:
            return all(self.is_safe(binding, scope) for binding in bindings)
        finally:
            self._resolving.discard(key)

    # -- results -----------------------------------------------------------

    def interpolations(self) -> list[Interpolation]:
        out: list[Interpolation] = []
        for function, fn in self.functions.items():
            for node in ast.walk(fn):
                if not isinstance(node, ast.JoinedStr):
                    continue
                out.extend(
                    self._classify(function, value)
                    for value in node.values
                    if isinstance(value, ast.FormattedValue)
                )
        return sorted(out, key=lambda item: (item.lineno, item.expression))

    def _classify(self, function: str, node: ast.FormattedValue) -> Interpolation:
        expression = ast.unparse(node.value)
        if (
            isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == ESCAPER
        ):
            verdict, reason = ESCAPED, f"{ESCAPER}() at the interpolation"
        elif _numeric_format(node.format_spec):
            verdict, reason = SAFE, f"numeric format spec :{_spec_text(node)}"
        elif self.is_safe(node.value, function):
            verdict, reason = SAFE, "provably not storage text"
        else:
            verdict, reason = RAW, "may be storage text, unescaped"
        return Interpolation(function, node.lineno, expression, verdict, reason)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _binding_pairs(node: ast.AST) -> list[tuple[str, ast.expr]]:
    """``(name, expression it can hold)`` for one statement of a function.

    A loop or comprehension target is approximated by the iterable itself:
    what this audit needs is "an element of a safe container is safe", and the
    container is what the source names. ``list.append`` and its siblings bind
    too -- without them ``cased: list[str] = []`` followed by
    ``cased.append(stored)`` would read as a safe empty list, which is exactly
    how ``title_case`` builds its result.
    """
    if isinstance(node, ast.Assign):
        return [
            (name, node.value)
            for target in node.targets
            for name in _target_names(target)
        ]
    if isinstance(node, ast.AnnAssign | ast.AugAssign | ast.NamedExpr):
        return (
            []
            if node.value is None
            else [(name, node.value) for name in _target_names(node.target)]
        )
    if isinstance(node, ast.For | ast.AsyncFor | ast.comprehension):
        return [(name, node.iter) for name in _target_names(node.target)]
    if isinstance(node, ast.withitem) and node.optional_vars is not None:
        return [(name, node.context_expr) for name in _target_names(node.optional_vars)]
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in MUTATORS
        and isinstance(node.func.value, ast.Name)
    ):
        return [(node.func.value.id, arg) for arg in node.args]
    return []


def _operands(node: ast.expr) -> list[ast.expr]:
    """The sub-expressions of a composite that can reach the output.

    An ``IfExp``'s test is deliberately absent: it decides *which* branch
    renders, it is never rendered itself.
    """
    if isinstance(node, ast.BinOp):
        return [node.left, node.right]
    if isinstance(node, ast.UnaryOp):
        return [node.operand]
    if isinstance(node, ast.BoolOp):
        return list(node.values)
    if isinstance(node, ast.IfExp):
        return [node.body, node.orelse]
    if isinstance(node, ast.List | ast.Tuple | ast.Set):
        return list(node.elts)
    return [node.elt]  # a comprehension: its element


def _args(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.arg]:
    spec = fn.args
    return [*spec.posonlyargs, *spec.args, *spec.kwonlyargs]


def _params(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    return [arg.arg for arg in _args(fn)]


def _annotation_types(node: ast.expr) -> frozenset[str]:
    """``Decimal | float | None`` -> ``{"Decimal", "float"}``.

    ``None`` is dropped: it renders as the empty string through ``_e`` and as
    the literal ``None`` otherwise, neither of which carries markup.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        text = node.value
    else:
        text = ast.unparse(node)
    return frozenset(part.strip() for part in text.split("|") if part.strip() != "None")


def _is_non_text(types: frozenset[str] | None) -> bool:
    """Is every alternative of this annotation a non-text type?"""
    return bool(types) and types <= NON_TEXT_ANNOTATIONS


def _target_names(target: ast.expr) -> list[str]:
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, ast.Tuple | ast.List):
        names: list[str] = []
        for element in target.elts:
            names.extend(_target_names(element))
        return names
    if isinstance(target, ast.Starred):
        return _target_names(target.value)
    return []


def _spec_text(node: ast.FormattedValue) -> str:
    spec = node.format_spec
    if spec is None:
        return ""
    return "".join(part.value for part in spec.values if isinstance(part, ast.Constant))


def _numeric_format(spec: ast.expr | None) -> bool:
    """Does ``spec`` force a numeric rendering, whatever the value is?"""
    if spec is None:
        return False
    if not isinstance(spec, ast.JoinedStr) or any(
        not isinstance(part, ast.Constant) for part in spec.values
    ):
        return False
    text = "".join(part.value for part in spec.values)
    return bool(text) and text[-1] in NUMERIC_PRESENTATIONS


#: The ordered dispatch :meth:`_Audit.is_safe` walks. First match wins, and
#: a node kind absent from it is unsafe -- new syntax has to be ruled on
#: rather than defaulting to "fine".
_RULES: tuple[tuple[type | tuple[type, ...], object], ...] = (
    ((ast.Constant, ast.Compare), _Audit._always_safe),
    ((ast.JoinedStr, ast.FormattedValue), _Audit._joined_safe),
    (
        (
            ast.BinOp,
            ast.UnaryOp,
            ast.BoolOp,
            ast.IfExp,
            ast.List,
            ast.Tuple,
            ast.Set,
            ast.GeneratorExp,
            ast.ListComp,
            ast.SetComp,
        ),
        _Audit._composite_safe,
    ),
    ((ast.Call,), _Audit._call_safe),
    ((ast.Name,), _Audit._name_lookup),
    ((ast.Subscript,), _Audit._subscript_safe),
    ((ast.Attribute,), _Audit._attribute_safe),
)


# ---------------------------------------------------------------------------
# public surface
# ---------------------------------------------------------------------------


def audit(tree: ast.Module) -> list[Interpolation]:
    """Every interpolation of every f-string in ``tree``, classified."""
    return _Audit(tree).interpolations()


def escape_call_sites(tree: ast.Module) -> list[int]:
    """The line of each ``_e(...)`` call, in :func:`ast.walk` order.

    The position in this list is the index :func:`without_escape` mutates, so
    the two share one traversal order by construction.
    """
    return [node.lineno for node in _escape_calls(tree)]


def escape_calls_at_interpolations(tree: ast.Module) -> list[int]:
    """The line of each ``_e(...)`` that is a ``{...}``'s whole expression.

    A subset of :func:`escape_call_sites`: an ``_e()`` inside a ``join``'s
    generator, or assigned to a local that is interpolated later, escapes just
    as much but is not itself an interpolation, so it produces no ``ESCAPED``
    verdict. Counting the two separately is what lets a test state the real
    relation between them instead of asserting ``16 <= 20``.
    """
    return [
        node.value.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.FormattedValue)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == ESCAPER
    ]


def without_escape(tree: ast.Module, index: int) -> ast.Module:
    """``tree`` with the ``index``-th ``_e(value)`` replaced by ``value``.

    The single-character mutation the audit has to notice, applied to a copy
    so one parse of the real module serves every case.
    """
    mutated = copy.deepcopy(tree)
    target = _escape_calls(mutated)[index]
    replacement = target.args[0]

    class _Strip(ast.NodeTransformer):
        def visit_Call(self, node: ast.Call) -> ast.AST:
            self.generic_visit(node)
            return replacement if node is target else node

    return ast.fix_missing_locations(_Strip().visit(mutated))


def _escape_calls(tree: ast.Module) -> list[ast.Call]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == ESCAPER
        and len(node.args) == 1
    ]
