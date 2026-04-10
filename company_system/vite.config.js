import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
    plugins: [react()],
    build: {
        outDir: 'staticfiles/js/reactflow',
        emptyOutDir: true,
        rollupOptions: {
            input: path.resolve(__dirname, 'src/main.jsx'),
            output: {
                entryFileNames: 'remedial-flowchart-bundle.js',
                format: 'iife',
                name: 'RemedialFlowchartApp',
            },
        },
    },
    css: {
        devSourcemap: true,
    },
    resolve: {
        alias: {
            '@': path.resolve(__dirname, './src'),
        },
    },
});