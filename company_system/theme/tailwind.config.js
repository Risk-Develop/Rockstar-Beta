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
            animation: {
                blob: 'blob 7s infinite',
                float: 'float 6s ease-in-out infinite',
            },
            keyframes: {
                blob: {
                    '0%': { transform: 'translate(0px, 0px) scale(1)' },
                    '33%': { transform: 'translate(30px, -50px) scale(1.1)' },
                    '66%': { transform: 'translate(-20px, 20px) scale(0.9)' },
                    '100%': { transform: 'translate(0px, 0px) scale(1)' },
                },
                float: {
                    '0%': { transform: 'translateY(0px) rotate(0deg)', opacity: '0' },
                    '10%': { opacity: '1' },
                    '90%': { opacity: '1' },
                    '100%': { transform: 'translateY(-100px) rotate(360deg)', opacity: '0' },
                },
            },
            transitionDelay: {
                '2000': '2s',
                '4000': '4s',
            }
        },
    },
    plugins: [
        require('flowbite/plugin')
    ],
}
