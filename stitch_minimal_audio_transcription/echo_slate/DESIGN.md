# Design System Specification: The Sonic Gallery

## 1. Overview & Creative North Star: "The Sonic Gallery"
The core philosophy of this design system is **The Sonic Gallery**. In an audio transcription environment, the user’s primary task is focused translation—turning sound into structure. We treat the interface not as a utility tool, but as a curated editorial space where whitespace represents silence and typography represents the clarity of the spoken word.

We break the "standard SaaS" look by rejecting rigid grids and heavy borders. Instead, we use **Intentional Asymmetry** and **Tonal Depth**. By overlapping elements and using extreme shifts in typographic scale, we create a sense of professional authority. This system isn't just "minimalist"; it is "reductionist"—stripping away the unnecessary to let the content breathe.

---

## 2. Colors: Signal & Silence
Our palette is rooted in the interplay between deep "Signal" blues and airy "Silence" grays.

*   **Primary Signal (`primary`: #0053db):** Used sparingly for high-intent actions. It represents the active state of sound.
*   **The Neutrals:** We rely on `surface` (#f7f9fb) and `on-surface` (#2a3439) to provide a high-contrast, editorial feel that mimics premium stationery.
*   **The "No-Line" Rule:** To achieve a high-end feel, **1px solid borders are prohibited** for sectioning. Boundaries must be defined solely through background color shifts. For example, a transcription panel (`surface-container-low`) should sit against the main app background (`surface`) without a stroke.
*   **Surface Hierarchy & Nesting:** Treat the UI as layers of fine paper. 
    *   **Base:** `surface` (#f7f9fb)
    *   **Sectioning:** `surface-container-low` (#f0f4f7)
    *   **Interaction Hubs:** `surface-container-highest` (#d9e4ea)
*   **The "Glass & Gradient" Rule:** Floating panels (like audio playback controls) should use a semi-transparent `surface` color with a `backdrop-blur` of 20px. For main CTAs, use a subtle linear gradient from `primary` (#0053db) to `primary_dim` (#0048c1) at a 135-degree angle to add "soul" and depth.

---

## 3. Typography: Editorial Clarity
We use **Inter** exclusively to bridge the gap between technical precision and human readability.

*   **Display Scales:** Use `display-lg` (3.5rem) for empty states or dashboard greetings to create an "editorial splash" feel.
*   **The Hierarchy:** 
    *   **Headlines:** Use `headline-sm` (1.5rem) for document titles. These should have a tight letter-spacing (-0.02em) to feel "locked-in."
    *   **Body:** `body-lg` (1rem) is the workhorse for the transcription text itself. Ensure a line-height of 1.6 to prevent eye fatigue during long reading sessions.
    *   **Labels:** `label-md` (0.75rem) should be used for timestamps and metadata, often in `on-surface-variant` (#566166) to recede visually.

---

## 4. Elevation & Depth: Tonal Layering
Traditional drop shadows are often a crutch for poor layout. This system prioritizes **Tonal Layering**.

*   **The Layering Principle:** Instead of a shadow, place a `surface-container-lowest` (#ffffff) card on a `surface-container` (#e8eff3) background. The 4% shift in value is enough to signify depth to the human eye while maintaining a clean aesthetic.
*   **Ambient Shadows:** If an element must float (e.g., a context menu), use an extra-diffused shadow: `box-shadow: 0 12px 40px rgba(42, 52, 57, 0.06)`. The shadow color is a low-opacity version of `on-surface`, never pure black.
*   **The "Ghost Border" Fallback:** If accessibility requires a container boundary, use a **Ghost Border**: `outline-variant` (#a9b4b9) at 20% opacity. It should be felt, not seen.
*   **Glassmorphism:** Use `surface_bright` at 80% opacity with a blur to create "Frosted Glass" overlays for audio waveform seek-bars, allowing the transcription text to subtly bleed through.

---

## 5. Components: Precision Primitives

### Buttons
*   **Primary:** Background `primary` (#0053db), text `on-primary`. Corner radius `md` (0.75rem).
*   **Secondary:** Background `secondary-container` (#d5e3fc), text `on-secondary-container`. 
*   **Tertiary:** No background. Text `primary`. Use for low-emphasis actions like "Cancel" or "Export."

### Audio Transcription Cards
*   **Rule:** No dividers between items. 
*   **Structure:** Use vertical whitespace (32px) and a background shift to `surface-container-low` on hover to define the list item.
*   **Typography:** The transcript snippet uses `body-lg`, while the filename uses `title-sm`.

### Input Fields (Search/Edit)
*   **Style:** Background `surface-container-highest` (#d9e4ea). No border.
*   **Focus State:** A 2px "Ghost Border" using `primary` at 40% opacity. 

### Audio Progress Bar
*   **Track:** `surface-variant` (#d9e4ea).
*   **Progress:** `primary` (#0053db).
*   **Knob:** A clean `surface-container-lowest` circle with a subtle `primary` ambient shadow.

---

## 6. Do's and Don'ts

### Do:
*   **Use Whitespace as a Tool:** If two elements feel cluttered, add 16px of space before reaching for a line.
*   **Align to the Type Baseline:** Ensure all icon-plus-text pairings are baseline-aligned to maintain the editorial "row" feel.
*   **Embrace Asymmetry:** It is acceptable to have a wide left margin for a "Table of Contents" and a narrow right margin for "Metadata."

### Don't:
*   **Don't use pure black (#000000):** Use `on-surface` (#2a3439) for text to keep the contrast sophisticated rather than harsh.
*   **Don't use default 1px borders:** Use background tone shifts. If you find yourself adding a border, ask "Can I use a 2% color shift instead?"
*   **Don't crowd the transcript:** The transcription text is the "Hero." Give it at least 80px of padding on either side to simulate a book page.