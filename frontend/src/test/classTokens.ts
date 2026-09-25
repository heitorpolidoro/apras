/**
 * The element's classes as the **whitespace-split token list** the browser
 * applies, never as one string.
 *
 * `className.toContain(...)` is a substring match, so the bare brand *surface*
 * token is satisfied vacuously by `text-primary-text` and by
 * `text-primary-foreground` — it could not tell the surface token from the
 * text token, which is exactly the distinction APRAS-87 introduced at these
 * call sites. Splitting on whitespace first is what makes a negative
 * assertion mean anything.
 *
 * Shared because `Navbar.test.tsx` and `Sidebar.test.tsx` assert over the same
 * active-item classes and must not drift apart in how they read them.
 *
 * (Spelled without the bare token literal on purpose: this file is swept by
 * `src/__tests__/brandTextRole.test.ts`, which counts occurrences in the text
 * of a source file, comments included.)
 */
export const classTokens = (element: Element): string[] =>
  element.className.split(/\s+/).filter(Boolean);
