// rollup.config.mjs — single entry (simple and safe)
import resolve from "@rollup/plugin-node-resolve";
import typescript from "@rollup/plugin-typescript";
import terser from "@rollup/plugin-terser";

const isProd = process.env.NODE_ENV === "production";

export default {
  input: "src/playtopro-card.ts",
  output: {
    // ⬇️ Build straight into the integration so HA can auto-load it
    file: "custom_components/playtopro/frontend/playtopro-card.js",
    format: "es",
    sourcemap: !isProd ? "inline" : true,
    inlineDynamicImports: true, // fold everything into one file
  },
  plugins: [
    resolve({ extensions: [".mjs", ".js", ".ts"] }),
    typescript({ tsconfig: "tsconfig.json", sourceMap: !isProd, inlineSources: !isProd }),
    isProd && terser(),
  ],
};