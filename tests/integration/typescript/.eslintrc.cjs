module.exports = {
  root: true,
  env: {
    node: true,
    es2022: true,
  },
  parser: '@typescript-eslint/parser',
  parserOptions: {
    ecmaVersion: 2022,
    sourceType: 'module',
    project: './tsconfig.json',
    tsconfigRootDir: __dirname,
  },
  plugins: ['@typescript-eslint'],
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
  ],
  rules: {
    // Allow unused vars starting with underscore
    '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
    // Allow any type in tests
    '@typescript-eslint/no-explicit-any': 'off',
    // Allow empty functions in tests
    '@typescript-eslint/no-empty-function': 'off',
  },
  ignorePatterns: [
    'node_modules/',
    'dist/',
    '*.cjs',
  ],
};
