import React, { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  CheckCheck,
  ClipboardPaste,
  OctagonX,
  Palette,
  RotateCcw,
  Save,
  ShieldCheck,
  TriangleAlert,
  Undo2,
} from "lucide-react";
import {
  BRAND_AUTHORED_KEYS,
  isValidHexColor,
  type BrandPalette,
  type BrandPaletteKey,
  type BrandTheme,
  type BrandContrastFailure,
  type DerivedTheme,
  type TenantProfile,
} from "../../../api/tenantProfile";
import {
  auditHexPalette,
  auditScheme,
  contrastRatio,
  hexPaletteToScheme,
  MEASURED_PAIRS,
  MINIMUM_CONTRAST_RATIO,
  oklchToHex,
  parseOklch,
  type ContrastFailure,
} from "../../../lib/contrast";
import {
  parseBrandPalettePaste,
  type PasteProblem,
} from "../../../lib/brandPalettePaste";
import { useUpdateTenantProfile } from "../../../hooks/useTenantProfile";

/**
 * "Cores da marca" — the two-mode colour section of the condominium profile
 * (APRAS-68).
 *
 * A child component rather than another four hundred lines inside
 * `TenantProfilePage`: the section owns its own draft, its own measurement
 * and its own write, and shares nothing with the name/slug/logo half but the
 * profile it is handed.
 *
 * **What this file may and may not contain.** It measures; it never derives.
 * `app/core/branding.py` is the only theme derivation in the repository, and
 * the preview and the emitted variables shown here are the server's own
 * answer read back out of `profile.theme`. The live panel measures what the
 * person typed with `lib/contrast.ts`, which is pinned against the same
 * fixture the Python is — so "the save is disabled" and "the API answers 422"
 * are the same judgement, reached twice. When they disagree, the server wins
 * and its body is rendered verbatim (D-B).
 *
 * **Simple mode has no live panel and must not have one.** There the
 * derivation owns both sides of every measured pair, so contrast cannot fail
 * by construction — and the client cannot compute those pairs anyway without
 * porting the derivation, which is exactly what D-D forbids. What is shown
 * instead is the measurement of the scheme the server last returned.
 */

const DEFAULT_PRIMARY = "#7c3aed";
const DEFAULT_ACCENT = "#0ea5e9";

/** The starting palette of advanced mode when there is nothing to carry over:
 *  today's `index.css` light scheme, so the first edit is a change to what is
 *  already on screen rather than to a blank form. */
const DEFAULT_PALETTE: BrandPalette = {
  background: "#fbfdfc",
  foreground: "#141a17",
  card: "#ffffff",
  "card-foreground": "#141a17",
  primary: "#0f8b5f",
  "primary-foreground": "#fafafa",
  secondary: "#eaf5ef",
  "secondary-foreground": "#1d2a23",
  accent: "#eaf5ef",
  "accent-foreground": "#1d2a23",
  muted: "#eef4f1",
  "muted-foreground": "#6b7772",
  border: "#dfe8e3",
};

type Mode = "simple" | "advanced";

interface Draft {
  /** Carried with the draft so a tenant switch cannot leave a palette typed
   *  against the previous condominium on screen — the same rule the name and
   *  slug draft follows in `TenantProfilePage`. */
  tenantId: string;
  mode: Mode;
  primary: string;
  accent: string;
  light: BrandPalette;
  dark: BrandPalette;
  deriveDark: boolean;
}

/** The hex the fields start at, derived from what the tenant already has. */
const draftFor = (profile: TenantProfile): Draft => {
  // `?? null` rather than a bare read: a payload that predates this task, or
  // a fixture that does, carries neither key, and "absent" has to mean the
  // same thing as "no colours" — otherwise an older server would crash the
  // screen instead of rendering the default palette.
  const stored = profile.brand_theme ?? null;
  const derived = profile.theme ?? null;
  const carried: BrandPalette = derived
    ? (Object.fromEntries(
        BRAND_AUTHORED_KEYS.map((key) => {
          const colour = parseOklch(derived.light[key] ?? "");
          return [key, colour === null ? DEFAULT_PALETTE[key] : oklchToHex(colour)];
        }),
      ) as BrandPalette)
    : DEFAULT_PALETTE;
  const carriedDark: BrandPalette = derived
    ? (Object.fromEntries(
        BRAND_AUTHORED_KEYS.map((key) => {
          const colour = parseOklch(derived.dark[key] ?? "");
          return [key, colour === null ? DEFAULT_PALETTE[key] : oklchToHex(colour)];
        }),
      ) as BrandPalette)
    : DEFAULT_PALETTE;

  if (stored?.mode === "advanced") {
    return {
      tenantId: profile.id,
      mode: "advanced",
      primary: stored.light.primary,
      accent: stored.light.secondary,
      light: stored.light,
      dark: stored.dark ?? carriedDark,
      deriveDark: stored.dark === null,
    };
  }
  return {
    tenantId: profile.id,
    mode: "simple",
    primary: stored?.primary ?? DEFAULT_PRIMARY,
    accent: stored?.accent ?? DEFAULT_ACCENT,
    light: carried,
    dark: carriedDark,
    deriveDark: true,
  };
};

/** What would be sent, given a draft. Built in one place so the disabled state
 *  and the request can never be computed from different things. */
const bodyFor = (draft: Draft): BrandTheme =>
  draft.mode === "simple"
    ? { mode: "simple", primary: draft.primary, accent: draft.accent }
    : {
        mode: "advanced",
        light: draft.light,
        dark: draft.deriveDark ? null : draft.dark,
      };

/** The 422 body's `failures`, if this is one — `InsufficientContrastError`. */
const failuresOf = (error: unknown): BrandContrastFailure[] => {
  const response = (
    error as { response?: { status?: number; data?: { failures?: unknown } } }
  )?.response;
  if (response?.status !== 422 || !Array.isArray(response.data?.failures)) {
    return [];
  }
  return response.data.failures as BrandContrastFailure[];
};

interface PairReading {
  pair: string;
  ratio: number;
  passes: boolean;
}

/** Every measured pair of one emitted scheme with its ratio — the panel shows
 *  the passing ones too, so a person can see the margin and not only the
 *  refusal. */
const readingsOf = (scheme: Readonly<Record<string, string>>): PairReading[] => {
  const readings: PairReading[] = [];
  for (const [foreground, background] of MEASURED_PAIRS) {
    const text = parseOklch(scheme[foreground] ?? "");
    const surface = parseOklch(scheme[background] ?? "");
    if (text === null || surface === null) continue;
    const ratio = contrastRatio(text, surface);
    readings.push({
      pair: `${foreground}/${background}`,
      ratio: Number(ratio.toFixed(2)),
      passes: ratio >= MINIMUM_CONTRAST_RATIO,
    });
  }
  return readings;
};

const HexField: React.FC<{
  name: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
}> = ({ name, label, value, onChange }) => {
  const { t } = useTranslation();
  const id = `brand-hex-${name}`;
  const malformed = !isValidHexColor(value);
  return (
    <div className="space-y-1">
      <label className="block text-xs font-medium text-foreground" htmlFor={id}>
        {label}
      </label>
      <div className="flex items-center gap-2">
        <input
          type="color"
          aria-hidden="true"
          tabIndex={-1}
          // A malformed draft would make the native picker throw away the
          // text the person is mid-way through typing, so it only follows a
          // value that is already a colour.
          value={malformed ? "#000000" : value.toLowerCase()}
          onChange={(event) => onChange(event.target.value)}
          className="h-9 w-10 shrink-0 cursor-pointer rounded-md border border-input bg-background p-1"
        />
        <input
          id={id}
          data-brand-hex={name}
          value={value}
          spellCheck={false}
          onChange={(event) => onChange(event.target.value)}
          className={`w-full rounded-md border bg-background px-2 py-1.5 font-mono text-xs ${
            malformed ? "border-destructive" : "border-input"
          }`}
        />
      </div>
      {malformed && (
        <p className="text-[11px] font-medium text-destructive">
          {t("tenantProfile.brand.hexInvalid")}
        </p>
      )}
    </div>
  );
};

const PairList: React.FC<{
  title: string;
  readings: PairReading[];
  /** Marks each row, so a test can count the pairs of one list among the
   *  several the screen renders. */
  itemTestId?: string;
}> = ({ title, readings, itemTestId }) => {
  const { t } = useTranslation();
  return (
    <div>
      <h4 className="mb-1.5 text-xs font-semibold text-foreground">{title}</h4>
      <ul className="space-y-1">
        {readings.map((reading) => (
          <li
            key={reading.pair}
            data-testid={itemTestId}
            className={`rounded px-2 py-1 font-mono text-[11px] ${
              reading.passes
                ? "bg-muted text-muted-foreground"
                : "bg-destructive/10 font-semibold text-destructive"
            }`}
          >
            {reading.passes
              ? t("tenantProfile.brand.pairOk", {
                  pair: reading.pair,
                  ratio: reading.ratio.toFixed(2),
                })
              : t("tenantProfile.brand.pairFail", {
                  pair: reading.pair,
                  ratio: reading.ratio.toFixed(2),
                  minimum: MINIMUM_CONTRAST_RATIO,
                })}
          </li>
        ))}
      </ul>
    </div>
  );
};

const Preview: React.FC<{
  label: string;
  scheme: Record<string, string>;
  testId?: string;
}> = ({ label, scheme, testId }) => (
  <div
    data-testid={testId}
    className="rounded-lg border p-3"
    style={
      {
        background: scheme.background,
        color: scheme.foreground,
        borderColor: scheme.border,
      } as React.CSSProperties
    }
  >
    <p className="text-xs font-semibold">{label}</p>
    <div className="mt-2 flex gap-2">
      <span
        className="rounded px-2 py-1 text-[11px]"
        style={{
          background: scheme.primary,
          color: scheme["primary-foreground"],
        }}
      >
        {scheme.primary}
      </span>
      <span
        className="rounded px-2 py-1 text-[11px]"
        style={{
          background: scheme.secondary,
          color: scheme["secondary-foreground"],
        }}
      >
        {scheme.secondary}
      </span>
    </div>
  </div>
);

/** What the draft held before an "Aplicar", and what that apply wrote — the
 *  dialog's whole memory, dropped the moment it closes (APRAS-95). */
interface Applied {
  beforeLight: BrandPalette;
  beforeDark: BrandPalette;
  beforeDeriveDark: boolean;
  light: BrandPalette;
  /** `undefined`: the paste said nothing about dark. `null`: it said
   *  `"dark": null`, which is the derive-dark checkbox. */
  dark?: BrandPalette | null;
}

const Swatch: React.FC<{ colour: string }> = ({ colour }) => (
  <span
    aria-hidden="true"
    className="mr-1 inline-block h-3 w-3 shrink-0 rounded-sm border border-border align-middle"
    style={{ background: colour }}
  />
);

/** Which focusables the Tab cycle below may land on. */
const FOCUSABLE = "textarea, button:not([disabled]), [href], input:not([disabled])";

/**
 * The paste dialog (APRAS-95, operator decision B: a header button opening a
 * window over the thirteen fields).
 *
 * Shaped after the slug-change dialog `TenantProfilePage` hand-rolls — the same
 * `role`, `aria-modal` and `aria-labelledby`, mounted only while open —
 * because `components/ui/alert-modal.tsx` takes a `message` and one confirm
 * button and cannot host a form, and the project has no dialog primitive. What
 * that dialog lacks is added here and only here: initial focus, Escape, a Tab
 * cycle inside the panel, and focus returning to the opening button. The slug
 * dialog's own missing keyboard handling is **APRAS-98**.
 *
 * It **never closes by itself**. A grammar refusal keeps the text verbatim and
 * lists the problems; a successful apply switches to the result state, because
 * landing thirteen values silently behind a dialog is the failure mode this
 * whole feature exists to avoid.
 */
const BrandPasteDialog: React.FC<{
  text: string;
  problems: PasteProblem[];
  applied: Applied | null;
  onText: (text: string) => void;
  onApply: () => void;
  onUndo: (snapshot: Applied) => void;
  onClose: () => void;
}> = ({ text, problems, applied, onText, onApply, onUndo, onClose }) => {
  const { t } = useTranslation();
  const area = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    area.current?.focus();
  }, []);

  // Mirrors `AlertModal`'s handler: the dialog is the only thing on screen that
  // Escape can mean while it is open.
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  const cycleTab = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== "Tab") return;
    // `currentTarget` is the panel itself, so no ref and no null check: the
    // handler cannot fire for an element the panel does not contain.
    const stops = Array.from(
      event.currentTarget.querySelectorAll<HTMLElement>(FOCUSABLE),
    );
    const first = stops[0];
    const last = stops[stops.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  /** A problem's sentence. The scheme a fault was found in is named in the
   *  reader's own language rather than as the API's `light`/`dark`. */
  const sentence = (problem: PasteProblem) =>
    t(problem.key, {
      ...problem.params,
      ...(problem.params?.scheme === undefined
        ? {}
        : {
            scheme: t(
              problem.params.scheme === "dark"
                ? "tenantProfile.brand.darkPalette"
                : "tenantProfile.brand.lightPalette",
            ),
          }),
    });

  const readings = applied === null ? [] : readingsOf(hexPaletteToScheme(applied.light));
  const darkReadings =
    applied?.dark == null ? [] : readingsOf(hexPaletteToScheme(applied.dark));
  const failures = [...readings, ...darkReadings].filter((reading) => !reading.passes);
  const values = (applied?.dark == null ? 1 : 2) * BRAND_AUTHORED_KEYS.length;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="brand-paste-title"
      data-testid="brand-paste-dialog"
      // A token scrim, the way `Sidebar`'s own overlay is: the slug dialog
      // this one is shaped after still darkens with a raw palette class, which
      // is a logged `GAP-OVERLAY` row of the theme-token migration and not
      // something new code in a migrated tree may add (APRAS-85's guard).
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-background/80 p-4 backdrop-blur-sm"
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        onKeyDown={cycleTab}
        className="my-8 w-full max-w-2xl space-y-4 rounded-xl bg-card p-6 shadow-xl"
      >
        <div className="flex items-start gap-3">
          <ClipboardPaste
            className="mt-0.5 h-5 w-5 shrink-0 text-muted-foreground"
            aria-hidden="true"
          />
          <h2 id="brand-paste-title" className="text-base font-semibold text-foreground">
            {t("tenantProfile.brand.paste.title")}
          </h2>
        </div>

        {applied === null ? (
          <div className="space-y-2">
            <p className="text-[11px] text-muted-foreground">
              {t("tenantProfile.brand.paste.hint")}
            </p>
            <textarea
              ref={area}
              data-brand-paste
              rows={10}
              spellCheck={false}
              aria-label={t("tenantProfile.brand.paste.textareaLabel")}
              value={text}
              onChange={(event) => onText(event.target.value)}
              className="w-full rounded-md border border-input bg-background p-2 font-mono text-[11px] leading-relaxed"
            />
            {problems.length > 0 && (
              <div
                role="alert"
                className="space-y-2 rounded-md border border-destructive/40 bg-destructive/10 p-3"
              >
                <p className="text-xs font-semibold text-destructive">
                  {t("tenantProfile.brand.paste.problemsTitle")}
                </p>
                <ul className="space-y-1">
                  {problems.map((problem) => (
                    <li
                      key={`${problem.key}-${JSON.stringify(problem.params ?? {})}`}
                      className="rounded bg-destructive/10 px-2 py-1 text-[11px] text-destructive"
                    >
                      {sentence(problem)}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <div className="flex justify-end gap-2 pt-1">
              <button
                type="button"
                onClick={onClose}
                className="rounded-md border border-input px-4 py-1.5 text-xs font-medium text-foreground"
              >
                {t("tenantProfile.brand.paste.cancel")}
              </button>
              <button
                type="button"
                onClick={onApply}
                className="rounded-md bg-primary px-4 py-1.5 text-xs font-medium text-primary-foreground"
              >
                {t("tenantProfile.brand.paste.apply")}
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <p
              className={`rounded-md px-3 py-2 text-xs font-medium ${
                failures.length > 0
                  ? "bg-destructive/10 text-destructive"
                  : "bg-muted text-primary-text"
              }`}
            >
              {failures.length > 0
                ? t("tenantProfile.brand.paste.appliedFail", {
                    values,
                    failures: failures.length,
                  })
                : t("tenantProfile.brand.paste.appliedOk", { values })}
            </p>

            <div>
              <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                {t("tenantProfile.brand.paste.appliedTitle")}
              </p>
              <div className="max-h-56 overflow-auto rounded-md border border-border">
                <table className="w-full text-left font-mono text-[11px]">
                  <thead className="bg-muted text-muted-foreground">
                    <tr>
                      <th className="px-2 py-1 font-sans font-medium">
                        {t("tenantProfile.brand.paste.columnKey")}
                      </th>
                      <th className="px-2 py-1 font-sans font-medium">
                        {t("tenantProfile.brand.paste.columnBefore")}
                      </th>
                      <th className="px-2 py-1 font-sans font-medium">
                        {t("tenantProfile.brand.paste.columnAfter")}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {BRAND_AUTHORED_KEYS.map((key) => {
                      const changed = applied.beforeLight[key] !== applied.light[key];
                      return (
                        <tr key={key} className="border-t border-border">
                          <td className="px-2 py-1 font-sans">
                            {key}
                            {changed && (
                              <span className="ml-1 text-[10px] font-medium text-primary-text">
                                {t("tenantProfile.brand.paste.changed")}
                              </span>
                            )}
                          </td>
                          <td className="px-2 py-1 text-muted-foreground">
                            <Swatch colour={applied.beforeLight[key]} />
                            {applied.beforeLight[key]}
                          </td>
                          <td className="px-2 py-1 text-foreground">
                            <Swatch colour={applied.light[key]} />
                            {applied.light[key]}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <div>
                <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                  {t("tenantProfile.brand.paste.previewTitle")}
                </p>
                <div className="space-y-2">
                  <Preview
                    label={t("tenantProfile.brand.paste.draftLight")}
                    scheme={applied.light}
                    testId="brand-paste-preview"
                  />
                  {applied.dark != null && (
                    <Preview
                      label={t("tenantProfile.brand.paste.draftDark")}
                      scheme={applied.dark}
                    />
                  )}
                </div>
              </div>
              <div className="space-y-2">
                <PairList
                  title={t("tenantProfile.brand.paste.pairsTitle")}
                  readings={readings}
                  itemTestId="brand-paste-pair"
                />
                {applied.dark != null && (
                  <PairList
                    title={t("tenantProfile.brand.pairsDark")}
                    readings={darkReadings}
                  />
                )}
              </div>
            </div>

            {failures.length > 0 && (
              <div className="rounded-md border-2 border-destructive/40 bg-destructive/10 p-3">
                <p className="text-xs font-semibold text-destructive">
                  {t("tenantProfile.brand.refusalTitle")}
                </p>
                <p className="mt-1 text-[11px] text-destructive">
                  {t("tenantProfile.brand.refusalBody", { count: failures.length })}
                </p>
                <p className="mt-1 text-[11px] text-destructive">
                  {t("tenantProfile.brand.paste.cannotSave")}
                </p>
              </div>
            )}

            <div className="flex justify-end gap-2 pt-1">
              <button
                type="button"
                onClick={() => onUndo(applied)}
                className="inline-flex items-center gap-1.5 rounded-md border border-input px-4 py-1.5 text-xs font-medium text-foreground"
              >
                <Undo2 className="h-3.5 w-3.5" aria-hidden="true" />
                {t("tenantProfile.brand.paste.undo")}
              </button>
              <button
                type="button"
                onClick={onClose}
                className="rounded-md bg-primary px-4 py-1.5 text-xs font-medium text-primary-foreground"
              >
                {t("tenantProfile.brand.paste.close")}
              </button>
            </div>
            <p className="text-[11px] text-muted-foreground">
              {t("tenantProfile.brand.paste.dismissNote")}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

const TenantBrandColors: React.FC<{ profile: TenantProfile }> = ({ profile }) => {
  const { t } = useTranslation();
  const update = useUpdateTenantProfile();
  const [draft, setDraft] = useState<Draft | null>(null);
  const [apiFailures, setApiFailures] = useState<BrandContrastFailure[]>([]);
  const [savedKey, setSavedKey] = useState<string | null>(null);
  const [pasting, setPasting] = useState(false);
  const [pasteText, setPasteText] = useState("");
  const [pasteProblems, setPasteProblems] = useState<PasteProblem[]>([]);
  const [applied, setApplied] = useState<Applied | null>(null);
  const pasteButton = useRef<HTMLButtonElement>(null);

  // `?? null` rather than a bare read: a payload that predates this task
  // carries neither key, and "absent" has to mean the same thing as "no
  // colours" — otherwise an older server would crash the screen instead of
  // rendering the default palette.
  const stored = profile.brand_theme ?? null;

  // Render-time derivation rather than an effect: a tenant switch replaces the
  // payload under the same query key, and a palette typed against the previous
  // condominium must not survive it.
  const current =
    draft !== null && draft.tenantId === profile.id ? draft : draftFor(profile);

  const edit = (patch: Partial<Draft>) => {
    setApiFailures([]);
    setSavedKey(null);
    setDraft({ ...current, ...patch });
  };

  /** Reopening always starts from an empty textarea: a palette is pasted once,
   *  and keeping the previous text would invite applying it twice. */
  const openPaste = () => {
    setPasteText("");
    setPasteProblems([]);
    setApplied(null);
    setPasting(true);
  };

  /** Closing is **never** an undo: whatever was applied stays in the draft, and
   *  the snapshot that made "Desfazer" possible is dropped. Focus goes back to
   *  the button that opened the dialog. */
  const closePaste = () => {
    setPasting(false);
    setApplied(null);
    setPasteProblems([]);
    setPasteText("");
    pasteButton.current?.focus();
  };

  /**
   * "Aplicar": parse, and on success write the palette into the very draft the
   * thirteen pickers write to.
   *
   * A **grammar** refusal applies nothing. A **contrast** failure is not a
   * refusal to apply — the values land, the client then measures them, and the
   * section's existing `blocked` disables Save with no new code path.
   */
  const applyPaste = () => {
    const result = parseBrandPalettePaste(pasteText);
    if (!result.ok) {
      setPasteProblems(result.problems);
      setApplied(null);
      return;
    }
    setPasteProblems([]);
    const patch: Partial<Draft> = { light: result.light };
    if (result.dark === null) {
      patch.deriveDark = true;
    } else if (result.dark !== undefined) {
      patch.dark = result.dark;
      patch.deriveDark = false;
    }
    edit(patch);
    setApplied({
      beforeLight: current.light,
      beforeDark: current.dark,
      beforeDeriveDark: current.deriveDark,
      light: result.light,
      dark: result.dark,
    });
  };

  /** The one undo there is, and only while the dialog is open. The snapshot
   *  comes from the dialog, which is the only place it can be pressed. */
  const undoPaste = (snapshot: Applied) => {
    edit({
      light: snapshot.beforeLight,
      dark: snapshot.beforeDark,
      deriveDark: snapshot.beforeDeriveDark,
    });
    setApplied(null);
  };

  const editLight = (key: BrandPaletteKey, value: string) =>
    edit({ light: { ...current.light, [key]: value } });
  const editDark = (key: BrandPaletteKey, value: string) =>
    edit({ dark: { ...current.dark, [key]: value } });

  const typedColours =
    current.mode === "simple"
      ? [current.primary, current.accent]
      : [
          ...BRAND_AUTHORED_KEYS.map((key) => current.light[key]),
          ...(current.deriveDark
            ? []
            : BRAND_AUTHORED_KEYS.map((key) => current.dark[key])),
        ];
  const anyMalformed = typedColours.some((value) => !isValidHexColor(value));

  // Simple mode is never measured here: the derivation owns both sides of
  // every pair, so it cannot fail, and measuring it would mean porting the
  // derivation (D-D).
  const clientFailures: ContrastFailure[] =
    current.mode === "advanced" && !anyMalformed
      ? [
          ...auditHexPalette(current.light),
          ...(current.deriveDark ? [] : auditHexPalette(current.dark)),
        ]
      : [];

  const derived: DerivedTheme | null = profile.theme ?? null;
  const lightReadings = derived ? readingsOf(derived.light) : [];
  const darkReadings = derived ? readingsOf(derived.dark) : [];
  const derivedFailures = derived
    ? [...auditScheme(derived.light), ...auditScheme(derived.dark)]
    : [];

  const blocked = anyMalformed || clientFailures.length > 0;

  const save = () => {
    setApiFailures([]);
    update.mutate(
      { brand_theme: bodyFor(current) },
      {
        onSuccess: () => {
          setDraft(null);
          setSavedKey("tenantProfile.brand.saved");
        },
        onError: (error) => {
          setSavedKey(null);
          setApiFailures(failuresOf(error));
        },
      },
    );
  };

  const reset = () => {
    setApiFailures([]);
    update.mutate(
      { brand_theme: null },
      {
        onSuccess: () => {
          setDraft(null);
          setSavedKey("tenantProfile.brand.resetDone");
        },
        onError: () => setSavedKey(null),
      },
    );
  };

  const modeButton = (mode: Mode, key: string) => (
    <button
      type="button"
      aria-pressed={current.mode === mode}
      onClick={() => edit({ mode })}
      className={`rounded-md px-4 py-1.5 text-sm font-medium ${
        current.mode === mode
          ? "bg-card text-foreground shadow-sm"
          : "text-muted-foreground"
      }`}
    >
      {t(key)}
    </button>
  );

  return (
    <section
      aria-label={t("tenantProfile.brand.title")}
      className="rounded-xl border border-border bg-card shadow-sm"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-6 py-4">
        <div className="flex items-center gap-3">
          <Palette className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
          <div>
            <h2 className="text-lg font-semibold text-foreground">
              {t("tenantProfile.brand.title")}
            </h2>
            <p className="text-xs text-muted-foreground">
              {t("tenantProfile.brand.subtitle")}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Advanced mode only: there is nothing to paste into two pickers,
              and simple mode gets no draft preview either (see the header). */}
          {current.mode === "advanced" && (
            <button
              type="button"
              ref={pasteButton}
              data-testid="brand-paste-open"
              aria-haspopup="dialog"
              onClick={openPaste}
              className="inline-flex items-center gap-2 rounded-md border border-input px-3 py-1.5 text-xs font-medium text-foreground hover:bg-muted"
            >
              <ClipboardPaste className="h-3.5 w-3.5" aria-hidden="true" />
              {t("tenantProfile.brand.paste.open")}
            </button>
          )}
          <div
            role="group"
            aria-label={t("tenantProfile.brand.modeLabel")}
            className="inline-flex rounded-lg border border-input bg-muted p-1"
          >
            {modeButton("simple", "tenantProfile.brand.modeSimple")}
            {modeButton("advanced", "tenantProfile.brand.modeAdvanced")}
          </div>
        </div>
      </div>

      {pasting && (
        <BrandPasteDialog
          text={pasteText}
          problems={pasteProblems}
          applied={applied}
          onText={setPasteText}
          onApply={applyPaste}
          onUndo={undoPaste}
          onClose={closePaste}
        />
      )}

      <div className="grid gap-8 px-6 py-6 lg:grid-cols-[minmax(0,380px)_1fr]">
        <div className="space-y-4">
          {current.mode === "simple" ? (
            <>
              <p className="flex items-start gap-2 rounded-md bg-muted px-3 py-2 text-xs text-muted-foreground">
                <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                <span>{t("tenantProfile.brand.simpleNote")}</span>
              </p>
              <HexField
                name="primary"
                label={t("tenantProfile.brand.primaryLabel")}
                value={current.primary}
                onChange={(value) => edit({ primary: value })}
              />
              <HexField
                name="accent"
                label={t("tenantProfile.brand.accentLabel")}
                value={current.accent}
                onChange={(value) => edit({ accent: value })}
              />
              <p className="text-xs text-muted-foreground">
                {t("tenantProfile.brand.accentHint")}
              </p>
            </>
          ) : (
            <>
              <p className="flex items-start gap-2 rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-900">
                <TriangleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                <span>{t("tenantProfile.brand.advancedNote")}</span>
              </p>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                {t("tenantProfile.brand.lightPalette")}
              </h3>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                {BRAND_AUTHORED_KEYS.map((key) => (
                  <HexField
                    key={key}
                    name={key}
                    label={t(`tenantProfile.brand.keys.${key}`)}
                    value={current.light[key]}
                    onChange={(value) => editLight(key, value)}
                  />
                ))}
              </div>
              <label className="flex items-start gap-2 rounded-md border border-border px-3 py-2 text-xs text-muted-foreground">
                <input
                  type="checkbox"
                  // The visible label carries the explanation as well, so the
                  // accessible name is set explicitly rather than inherited
                  // from a paragraph of prose.
                  aria-label={t("tenantProfile.brand.deriveDark")}
                  checked={current.deriveDark}
                  onChange={(event) => edit({ deriveDark: event.target.checked })}
                  className="mt-0.5"
                />
                <span>
                  <span className="font-medium text-foreground">
                    {t("tenantProfile.brand.deriveDark")}
                  </span>{" "}
                  {t("tenantProfile.brand.deriveDarkHint")}
                </span>
              </label>
              {!current.deriveDark && (
                <>
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    {t("tenantProfile.brand.darkPalette")}
                  </h3>
                  <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                    {BRAND_AUTHORED_KEYS.map((key) => (
                      <HexField
                        key={`dark-${key}`}
                        name={`dark-${key}`}
                        label={t(`tenantProfile.brand.keys.${key}`)}
                        value={current.dark[key]}
                        onChange={(value) => editDark(key, value)}
                      />
                    ))}
                  </div>
                </>
              )}
            </>
          )}

          <p className="text-xs text-muted-foreground">
            {t("tenantProfile.brand.hexHint")}
          </p>

          <div className="space-y-2 border-t border-border pt-4">
            <button
              type="button"
              onClick={save}
              disabled={blocked || update.isPending}
              className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Save className="h-4 w-4" aria-hidden="true" />
              {t("tenantProfile.brand.save")}
            </button>
            {stored !== null && (
              <button
                type="button"
                onClick={reset}
                disabled={update.isPending}
                className="inline-flex w-full items-center justify-center gap-2 rounded-md border border-destructive/30 px-3 py-2 text-sm font-medium text-destructive hover:bg-destructive/10 disabled:opacity-60"
              >
                <RotateCcw className="h-4 w-4" aria-hidden="true" />
                {t("tenantProfile.brand.reset")}
              </button>
            )}
            {savedKey && (
              <p role="status" className="text-center text-xs font-medium text-emerald-700">
                {t(savedKey)}
              </p>
            )}
          </div>
        </div>

        <div className="space-y-4">
          {(clientFailures.length > 0 || apiFailures.length > 0) && (
            <div
              role="alert"
              className="rounded-lg border-2 border-destructive/40 bg-destructive/10 p-4"
            >
              <div className="flex items-start gap-3">
                <OctagonX
                  className="mt-0.5 h-5 w-5 shrink-0 text-destructive"
                  aria-hidden="true"
                />
                <div className="space-y-1">
                  <p className="text-sm font-semibold text-destructive">
                    {t("tenantProfile.brand.refusalTitle")}
                  </p>
                  <p className="text-xs text-destructive">
                    {t("tenantProfile.brand.refusalBody", {
                      count: Math.max(clientFailures.length, apiFailures.length),
                    })}
                  </p>
                  <ul className="space-y-1 pt-1">
                    {[...apiFailures, ...clientFailures].map((failure, index) => (
                      <li
                        key={`${failure.pair}-${index}`}
                        className="rounded bg-destructive/10 px-2 py-1 font-mono text-[11px] text-destructive"
                      >
                        {t("tenantProfile.brand.pairFail", {
                          pair: failure.pair,
                          ratio: failure.ratio.toFixed(2),
                          minimum: failure.minimum,
                        })}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}

          {clientFailures.length === 0 && apiFailures.length === 0 && (
            <p className="flex items-start gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-800">
              <CheckCheck className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              <span>{t("tenantProfile.brand.allPass")}</span>
            </p>
          )}

          {/* The draft preview: the authored hexes, painted verbatim. The
              `Preview` pair further down renders `profile.theme` — what the
              server answered — and a pasted palette has never been there. This
              derives nothing: in advanced mode `_advanced_scheme` emits the
              thirteen literally, so painting the typed hex is showing what was
              authored, not a port of the derivation (D-D). Simple mode gets
              none of it, the derivation owning both sides there. */}
          {current.mode === "advanced" && (
            <div>
              <h3 className="mb-2 text-sm font-semibold text-foreground">
                {t("tenantProfile.brand.paste.draftTitle")}
              </h3>
              <div className="grid gap-3 md:grid-cols-2">
                <Preview
                  label={t("tenantProfile.brand.paste.draftLight")}
                  scheme={current.light}
                  testId="brand-draft-preview"
                />
                {!current.deriveDark && (
                  <Preview
                    label={t("tenantProfile.brand.paste.draftDark")}
                    scheme={current.dark}
                  />
                )}
              </div>
            </div>
          )}

          {derived === null ? (
            <div className="rounded-lg border border-border bg-muted/40 p-4">
              <h3 className="text-sm font-semibold text-foreground">
                {t("tenantProfile.brand.noneTitle")}
              </h3>
              <p className="mt-1 text-xs text-muted-foreground">
                {t("tenantProfile.brand.noneBody")}
              </p>
            </div>
          ) : (
            <>
              <PairList
                title={t("tenantProfile.brand.pairsLight")}
                readings={lightReadings}
              />
              <PairList
                title={t("tenantProfile.brand.pairsDark")}
                readings={darkReadings}
              />
              {derivedFailures.length === 0 && (
                <p className="sr-only">{t("tenantProfile.brand.allPass")}</p>
              )}
              <div>
                <h3 className="mb-2 text-sm font-semibold text-foreground">
                  {t("tenantProfile.brand.previewTitle")}
                </h3>
                <div className="grid gap-3 md:grid-cols-2">
                  <Preview
                    label={t("tenantProfile.brand.previewLight")}
                    scheme={derived.light}
                  />
                  <Preview
                    label={t("tenantProfile.brand.previewDark")}
                    scheme={derived.dark}
                  />
                </div>
              </div>
              <details className="rounded-lg border border-border p-3 text-xs">
                <summary className="cursor-pointer font-medium text-foreground">
                  {t("tenantProfile.brand.emittedTitle")}
                </summary>
                <pre className="mt-2 overflow-x-auto text-[11px] leading-relaxed text-muted-foreground">
                  {Object.entries(derived.light)
                    .map(([name, value]) => `--${name}: ${value};`)
                    .join("\n")}
                </pre>
              </details>
            </>
          )}
        </div>
      </div>
    </section>
  );
};

export default TenantBrandColors;
