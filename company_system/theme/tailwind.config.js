/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: 'class',
    content: [
        "../templates/**/*.html",
        "../../**/*.html",
        "./node_modules/flowbite/**/*.js",
        "./node_modules/flowbite-datepicker/**/*.js",
    ],
    theme: {
        extend: {
            colors: {
                // Add light mode variants through CSS custom properties if needed
            },
        },
    },
    plugins: [
        require('flowbite/plugin')
    ],
}
