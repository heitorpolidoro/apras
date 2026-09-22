import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  CheckCheck,
  OctagonX,
  Palette,
  RotateCcw,
  Save,
  ShieldCheck,
  TriangleAlert,
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
  MEASURED_PAIRS,
  MINIMUM_CONTRAST_RATIO,
  oklchToHex,
  parseOklch,
  type ContrastFailure,
} from "../../../lib/contrast";
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

const PairList: React.FC<{ title: string; readings: PairReading[] }> = ({
  title,
  readings,
}) => {
  const { t } = useTranslation();
  return (
    <div>
      <h4 className="mb-1.5 text-xs font-semibold text-foreground">{title}</h4>
      <ul className="space-y-1">
        {readings.map((reading) => (
          <li
            key={reading.pair}
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

const Preview: React.FC<{ label: string; scheme: Record<string, string> }> = ({
  label,
  scheme,
}) => (
  <div
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

const TenantBrandColors: React.FC<{ profile: TenantProfile }> = ({ profile }) => {
  const { t } = useTranslation();
  const update = useUpdateTenantProfile();
  const [draft, setDraft] = useState<Draft | null>(null);
  const [apiFailures, setApiFailures] = useState<BrandContrastFailure[]>([]);
  const [savedKey, setSavedKey] = useState<string | null>(null);

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
        <div
          role="group"
          aria-label={t("tenantProfile.brand.modeLabel")}
          className="inline-flex rounded-lg border border-input bg-muted p-1"
        >
          {modeButton("simple", "tenantProfile.brand.modeSimple")}
          {modeButton("advanced", "tenantProfile.brand.modeAdvanced")}
        </div>
      </div>

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
