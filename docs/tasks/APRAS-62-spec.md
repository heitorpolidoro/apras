# APRAS-62 — Task screen finishing: search, dragging, overdue and assignee

Interactive mockup: [`docs/tasks/APRAS-62-mock.html`](./APRAS-62-mock.html) —
five panels (search + chips, dragging, overdue states, assignee picker, empty
result), each with an annotation strip.

## Scope

Four gaps of the task screen (`frontend/src/features/task-management`), all on
one surface — the dashboard top bar, the board card and the task form:

1. **Search** — no free-text search exists; `useTaskFiltering.ts` filters only
   `status`/`priority`/`assigned_to_id`.
2. **Dragging** — `TaskBoard.tsx` has no drag-and-drop, so changing a status
   means opening the task, changing a `<select>` and saving, on a board that
   *is* the drag metaphor.
3. **Overdue** — the due date is raw `toLocaleDateString` text, so a task five
   days late has the visual weight of one due in two weeks.
4. **Assignee** — a plain `<select>` with everybody in it, under a helper key
   that says the field will be improved in a future version.

**No backend change and no schema change.** Every one of the four is rendered
or filtered from data `GET /api/v1/tasks/` and `GET /api/v1/users/` already
return, and the only write is the existing `PATCH /api/v1/tasks/{id}`.
**No new Alembic revision, and no column added to
`backend/alembic/versions/0001_initial_schema.py`** — this task needs no
column at all.

**Kept as one deliverable, deliberately.** It is four behaviours, but they
collide in the same four files (`TaskDashboard.tsx`, `TaskBoard.tsx`,
`TaskCard.tsx`, both locale JSONs), so splitting buys parallelism it cannot
use and pays for it in conflicts. Three scope decisions keep it PR-sized and
are binding:

- **No new npm dependency.** Dragging uses the native HTML5 drag-and-drop API
  (`draggable`, `dragstart`/`dragover`/`dragleave`/`drop`), which is
  `fireEvent`-drivable in jsdom; a dnd library (`@dnd-kit`, `react-beautiful-dnd`)
  is out of scope and would need pointer-event/measurement shims Vitest does
  not give.
- **Undo re-PATCHes**, it does not snapshot and replay a cache.
- The searchable assignee picker replaces the **form** field only; the
  dashboard's assignee *filter* stays the existing `<select>`.

## Approach

### Behaviour

**Two filter objects, not one.** `TaskDashboard` today holds a single
`filters` state that is both the `useTasks` query key and the client-side
filter. Search and the overdue toggle must not be in the query key, or every
keystroke refetches. `TaskDashboard` keeps `serverFilters`
(`status`, `priority`, `category_id`, `assigned_to_id` — the object passed to
`useTasks`, unchanged) and a new `clientFilters` (`search`, `overdueOnly`);
the merged object is what reaches `TaskBoard` / `TaskList`.
`TaskFilters` (`hooks/useTaskFiltering.ts`) gains optional `search?: string`
and `overdueOnly?: boolean`.

**Search.** A text input in the top bar, debounced ~200 ms, filtered
client-side in `useTaskFiltering` over the already-loaded tasks: a task
matches when the normalised search text is a substring of the normalised
`title` **or** `description`. Normalisation is lower-cased and
diacritic-stripped (`NFD` + `\p{Diacritic}` removal), so `manutencao` matches
`Manutenção`. Blank/whitespace-only search filters nothing. The matched
fragment is wrapped in a `<mark>` in the card title and description
(`TaskCard`) and in the list title and description cell (`TaskList`), through
one shared presentational helper.

**Filter summary.** The top bar states how many tasks the filters leave
visible out of the total (`"12 de 47 tarefas"`), and renders one removable
chip per active filter — status, priority, category, assignee, search text,
overdue-only — each naming the filter's human label and clearing only itself.
When the result is empty the bar's own summary and chips are still on screen,
so `tasks.list.emptyFiltered`'s dead end becomes "here is what is hiding them,
remove one".

**Card markup (binding: unchanged root).** Dragging is **mouse-only** — there is
no keyboard grab, by operator decision (2026-09-18) — and with no keyboard path
there is no drag-handle `<button>`, which was the *only* reason the earlier
draft restructured the card. So `TaskCard` keeps its current markup: the root
stays the single `<button>` it is today, and it simply gains the `draggable`
attribute plus the `dragstart`/`dragend` handlers.

This is sound, not a shortcut: `draggable` is a global HTML attribute, valid on
any element including a `<button>`, and the HTML5 drag source is whatever
element carries it — the spec has no notion of a separate handle. The one
implementation detail this makes binding is that the `dragstart` handler **must**
call `e.dataTransfer.setData("text/plain", task.id)`; without a payload Firefox
refuses to start the drag. Optionally the card may show a decorative grip icon
(`<span aria-hidden="true">`, never focusable, never a button) as a mouse
affordance.

Consequences: **no existing test changes.**
`__tests__/TaskCard.test.tsx:80`'s `screen.getByRole("button")` keeps matching
exactly one element, so the line stands as written and this task must not touch
it. There is no `task-card-open`, no `task-card-handle` and no `<article>` root
anywhere in this task.

**Dragging.** Each draggable `TaskCard` on the board is `draggable`; the drag is
started by pressing the mouse anywhere on the card. A click that does not move
still opens the task, unchanged. Dragging a card over a column highlights that column; the
origin position leaves a dashed placeholder gap; dropping on a column whose
status differs fires `PATCH /tasks/{id} {status}` optimistically (the cached
`["tasks", …]` lists are updated before the request and rolled back on
failure). Dropping on the origin column is a no-op and fires nothing. A card
rendered `readOnly` (the simulation lock) is not draggable and refuses the
drop. After a successful drop a confirmation strip names the move and offers
**Desfazer**, which PATCHes the task back to its previous status; the strip
auto-dismisses after ~8 s.

**Dragging is off when a status filter is active.** `TaskBoard` already renders
`visibleColumns = filters.status ? [the matching column] : columns`, so a
status filter leaves a single column on screen and there is nowhere to move a
card to. When `filters.status` is set, `TaskBoard` therefore renders its cards
with dragging disabled: no `draggable`, no drop targets. Instead the single
column's header carries a short hint
(`tasks.board.dragDisabledByStatusFilter`, e.g. "remova o filtro de situação
para mover tarefas").

Note why this survives the move to mouse-only. Its original justification was a
correctness one — arrow keys could traverse columns that were not rendered, so a
card could land in a hidden status — and that failure mode is now impossible by
construction, because a mouse drop target must be an element on screen. What is
left is a plain usability reason, and it is enough: a card that looks draggable
and has exactly one legal destination (its own column, a no-op) is a dead
affordance, and the hint names the reason instead of letting the user discover
it by failing. Every other filter (priority, category,
assignee, search, overdue) leaves all five columns visible and dragging fully
enabled — a card whose new status keeps it filtered out by one of *those*
filters is not possible either, since none of them depends on status.

**No keyboard equivalent, deliberately.** Dragging is a mouse shortcut, not a
new door: changing a task's status by keyboard stays exactly what it is on
master — open the task and switch the status `<select>` in `TaskForm`, which is
fully keyboard-operable. So the drag locks nobody out, and this task adds no
grab/move/drop key handling, no `aria-grabbed`, no arrow-key column traversal
and no live-region move announcements. `TaskCard`'s existing `handleKeyDown`
(`Enter`/`Space` open the task) is the card's only keyboard behaviour and is
untouched.

**Overdue.** A pure helper classifies a due date against "today" into
`overdue` / `today` / `tomorrow` / `soon` (≤ 7 days) / `future`, and returns
the whole-day distance. A task whose status is `COMPLETED` or `CANCELED` is
never overdue. The card and the list render the class as **text plus an icon,
never colour alone**: overdue reads relative with the word *atraso*
("5 dias em atraso"), `tomorrow` reads "vence amanhã", `today` "vence hoje",
`future` keeps the absolute `toLocaleDateString` it renders today. The top bar
shows a counter of overdue tasks (over the same visible set the summary
counts); clicking it toggles `clientFilters.overdueOnly` and it renders as a
chip like any other filter.

**Assignee picker.** A new combobox component replaces the `<select>` in
`TaskForm`: a text input filters the `useAssignableUsers` list by normalised
name or email, and the listbox renders one option per person with the initials
avatar, the full name and the role name(s) on their own line, plus an explicit
"deixar sem responsável" option that sets `assigned_to_id` to `null`. It is
keyboard-navigable (`ArrowUp`/`ArrowDown`/`Enter`/`Escape`), labelled by the
existing `tasks.form.assigneeLabel`, and submits the same
`assigned_to_id: string | null` `TaskForm` submits today — no payload change.
`tasks.form.assigneeHelper` is deleted from `pt.json` and `en.json`.

### Files touched

| File | What changes |
|---|---|
| `frontend/src/features/task-management/hooks/useTaskFiltering.ts` | `TaskFilters` gains `search` and `overdueOnly`; the predicate gains the normalised text match and the overdue match |
| `frontend/src/features/task-management/utils/taskUtils.ts` | adds `normalizeText`, `matchesSearch`, `dueDateState`/`isOverdue` and the relative-days helper |
| `frontend/src/features/task-management/components/TaskFilterBar.tsx` *(new)* | search input, chips, "X de Y" summary, overdue counter |
| `frontend/src/features/task-management/components/HighlightedText.tsx` *(new)* | wraps the matched fragment in `<mark>` |
| `frontend/src/features/task-management/components/DueDateBadge.tsx` *(new)* | icon + wording for each due-date state |
| `frontend/src/features/task-management/components/AssigneePicker.tsx` *(new)* | the searchable assignee combobox |
| `frontend/src/features/task-management/components/TaskDashboard.tsx` | splits `serverFilters` / `clientFilters`, renders `TaskFilterBar`, hosts the drop confirmation strip |
| `frontend/src/features/task-management/components/TaskBoard.tsx` | drop targets, column highlight, dashed origin gap, calls the status mutation; disables dragging and shows the header hint when `filters.status` is set |
| `frontend/src/features/task-management/components/TaskCard.tsx` | keeps its `<button>` root; adds `draggable` + `dragstart`/`dragend` (with `dataTransfer.setData`), `HighlightedText`, `DueDateBadge`, optional decorative grip |
| `frontend/src/features/task-management/components/__tests__/TaskCard.test.tsx` | new `<mark>`/due-date/`draggable` assertions only — **line 80 is not modified** |
| `frontend/src/features/task-management/components/TaskList.tsx` | `HighlightedText` in the title/description cell, `DueDateBadge` in the due-date cell |
| `frontend/src/features/task-management/components/TaskForm.tsx` | `AssigneePicker` replaces the `<select>`; the helper paragraph is removed |
| `frontend/src/features/task-management/hooks/useTasks.ts` | adds the optimistic status mutation (`onMutate` cache update, `onError` rollback, `onSettled` invalidate) |
| `frontend/src/i18n/locales/pt.json`, `frontend/src/i18n/locales/en.json` | `tasks.form.assigneeHelper` removed; new keys for search, chips, summary, overdue wording, `tasks.board.dragDisabledByStatusFilter`, drag/undo strip and the picker — added to **both**, key-identical |

Tests: new `__tests__` modules for `TaskFilterBar`, `AssigneePicker`,
`DueDateBadge`/`taskUtils` and the board's drag behaviour, plus additions to
`useTaskFiltering.test.ts`, `TaskCard.test.tsx`, `TaskDashboard.test.tsx` and
`TaskForm.test.tsx`.

### Test criteria

- `useTaskFiltering`: `"manutencao"` matches a task titled `Manutenção`;
  a description-only match is kept; a blank search keeps everything;
  `overdueOnly` keeps a past-due `PENDING` and drops a past-due `COMPLETED`.
- Due-date helper: a fixed "now" against past / today / tomorrow / +5d / +30d
  produces the five states and the expected day counts.
- `TaskCard`: renders a `<mark>` around the matched fragment; renders the
  overdue wording *and* an icon element (asserted by role/test-id, not by
  class colour).
- `TaskBoard`: `fireEvent.dragStart` on a card then `drop` on another column
  calls the mutation once with the destination status; dropping on the origin
  column calls nothing; a `readOnly` card is not `draggable`.
  With `filters.status` set, the board renders one column, no card is
  `draggable`, and the header hint is in the document.
- `TaskCard`: a rendered card exposes exactly one `button` role
  (`getAllByRole("button")` has length 1) and that root carries
  `draggable="true"`; the existing `Enter`/`Space` test at
  `TaskCard.test.tsx:80` passes **unmodified**; `ArrowLeft`/`ArrowRight` on the
  card call no mutation and change nothing.
- `TaskDashboard`: typing in the search input does not change the `useTasks`
  query key (the fetch mock is not called again); the summary text reports the
  filtered and total counts; clicking a chip's remove control clears that one
  filter and leaves the others; after a drop the strip renders and its
  *Desfazer* control PATCHes the original status back.
- `AssigneePicker`: typing part of a name narrows the options; each option
  renders name and role; choosing "deixar sem responsável" submits
  `assigned_to_id: null`; `TaskForm` submits the chosen id.
- i18n: `src/i18n/__tests__/parity.test.ts` stays green, and a test asserts
  `tasks.form.assigneeHelper` is absent from both locales.

## Expected Results

- [ ] The top bar carries a text search over title and description, case- and
      accent-insensitive, filtered client-side in `useTaskFiltering` with no
      refetch, and the matched fragment is rendered inside `<mark>` on the card.
- [ ] Each active filter renders as a removable chip and the bar states how
      many tasks are visible out of the total.
- [ ] A card dragged to another column highlights the destination, leaves a
      dashed gap at the origin, fires exactly one status `PATCH` on drop, and a
      confirmation strip offers *Desfazer*, which restores the previous status.
- [ ] Dragging is mouse-only: the card exposes no grab/move/drop key handling
      and no drag handle, and `ArrowLeft`/`ArrowRight` on a focused card fire no
      request.
- [ ] With a status filter active the board shows its single column with
      dragging disabled — no `draggable` card — and a header hint saying the
      status filter must be removed to move tasks.
- [ ] `TaskCard`'s root stays the single `<button>` it is on master, now
      carrying `draggable`, and it is still the only `button` role in a rendered
      card; `TaskCard.test.tsx:80` passes unmodified.
- [ ] A past-due task reads as relative time with an icon and the word
      *atraso*; one due tomorrow reads *vence amanhã*; a distant one keeps the
      absolute date; a `COMPLETED`/`CANCELED` task is never overdue.
- [ ] An overdue counter in the top bar filters the board when clicked.
- [ ] The form's assignee field is a searchable picker showing initials, name
      and role per option, with an explicit "no assignee" option.
- [ ] `tasks.form.assigneeHelper` is absent from `pt.json` and `en.json`, which
      stay key-identical.
- [ ] `npm run build` (`tsc -b`), `npm run test:coverage` (thresholds
      80/78/76/80) and the diff-scoped eslint check pass.

## Out of Scope

- Any backend, schema or Alembic change; any change to the task payload.
- A drag-and-drop library, and reordering *within* a column (the board has no
  task order field to persist).
- The dashboard's assignee **filter** select, which stays as it is.
- Server-side search (`?q=`) and pagination.
- Cleaning the pre-existing eslint debt: `npx eslint .` reports **375 errors
  across 64 files** on master, of which **126 in 10 already-existing
  `task-management` test files** (120 `@typescript-eslint/no-explicit-any`,
  5 `react-hooks/rules-of-hooks`, 1 `prefer-const`). The gate for this task is
  therefore diff-scoped: **zero findings in every file this task creates**, and
  **no increase** in the finding count of any file it edits — no new file may
  enter the failing set. Paying the debt off is a task of its own, the frontend
  mirror of APRAS-54.
