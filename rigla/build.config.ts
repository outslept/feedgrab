import { defineBuildConfig } from 'unbuild'

export default defineBuildConfig({
  entries: ['lib/index'],
  clean: true,
  rollup: {
    inlineDependencies: true,
    esbuild: {
      minify: true,
    },
  },
  declaration: true,
  outDir: 'dist',
})
