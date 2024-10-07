module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
    "node_modules/@radix-ui/react-*/*.js",
  ],
  theme: {
    extend: {},
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@radix-ui/react-dropdown-menu'),
    require('@radix-ui/react-tooltip'),
  ],
}
