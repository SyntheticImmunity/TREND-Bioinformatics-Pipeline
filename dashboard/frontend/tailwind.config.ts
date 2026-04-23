import type { Config } from "tailwindcss";

/**
 * Tailwind tokens derived from DESIGN.md. The brand is carried by:
 *   - Cream background (#f7f4ed)
 *   - Charcoal text (#1c1c1c) at varying opacity
 *   - Soft warm borders (#eceae4 passive, rgba(28,28,28,0.4) interactive)
 *   - Inset shadow on dark buttons (the signature tactile detail)
 *   - Inter (humanist fallback for Camera Plain Variable per plan kickoff Q2)
 */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        cream: {
          DEFAULT: "#f7f4ed",
          light: "#fcfbf8",
          border: "#eceae4",
        },
        charcoal: {
          DEFAULT: "#1c1c1c",
          83: "rgba(28, 28, 28, 0.83)",
          82: "rgba(28, 28, 28, 0.82)",
          40: "rgba(28, 28, 28, 0.4)",
          4: "rgba(28, 28, 28, 0.04)",
          3: "rgba(28, 28, 28, 0.03)",
        },
        muted: {
          DEFAULT: "#5f5f5d",
        },
      },
      fontFamily: {
        // Camera Plain Variable when licensed; Inter (loaded via index.html) is the
        // humanist fallback chosen at plan kickoff. Inter ships variable weights
        // so the 400/600 hierarchy in DESIGN.md still reads correctly.
        sans: [
          "Inter var",
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif",
        ],
        display: [
          "Inter var",
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "sans-serif",
        ],
      },
      fontSize: {
        // From DESIGN.md typography hierarchy table.
        "display-hero": ["3.75rem", { lineHeight: "1.05", letterSpacing: "-0.0375rem" }],
        "display-section": ["3rem", { lineHeight: "1.0", letterSpacing: "-0.03rem" }],
        "display-sub": ["2.25rem", { lineHeight: "1.1", letterSpacing: "-0.0225rem" }],
        "card-title": ["1.25rem", { lineHeight: "1.25" }],
        "body-lg": ["1.125rem", { lineHeight: "1.38" }],
      },
      borderRadius: {
        // From DESIGN.md radius scale.
        micro: "4px",
        standard: "6px",
        comfortable: "8px",
        card: "12px",
        container: "16px",
      },
      boxShadow: {
        // Signature inset shadow on dark buttons (DESIGN.md §4 Buttons).
        "button-inset":
          "rgba(255,255,255,0.2) 0px 0.5px 0px 0px inset, rgba(0,0,0,0.2) 0px 0px 0px 0.5px inset, rgba(0,0,0,0.05) 0px 1px 2px 0px",
        // Soft, warm focus ring.
        focus: "rgba(0,0,0,0.1) 0px 4px 12px",
      },
      spacing: {
        // The expansive end of the DESIGN.md spacing scale.
        18: "4.5rem",   // 72
        22: "5.5rem",   // 88
        30: "7.5rem",   // 120
        38: "9.5rem",   // 152
        44: "11rem",    // 176
        52: "13rem",    // 208
      },
    },
  },
  plugins: [],
} satisfies Config;
