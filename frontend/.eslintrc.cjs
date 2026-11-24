module.exports = {
  root: true,
  env: {
    browser: true,
    es2022: true,
  },
  parserOptions: {
    ecmaVersion: "latest",
    sourceType: "module",
    ecmaFeatures: { jsx: true },
  },
  rules: {
    "no-restricted-globals": [
      "error",
      {
        name: "localStorage",
        message: "Civisterial forbids localStorage; keep results in React state only.",
      },
      {
        name: "sessionStorage",
        message: "Civisterial forbids sessionStorage; keep results in React state only.",
      },
      {
        name: "gtag",
        message: "Analytics scripts are forbidden in Civisterial.",
      },
      {
        name: "ga",
        message: "Analytics scripts are forbidden in Civisterial.",
      },
    ],
    "no-restricted-properties": [
      "error",
      {
        object: "window",
        property: "localStorage",
        message: "Civisterial forbids localStorage; keep results in React state only.",
      },
      {
        object: "window",
        property: "sessionStorage",
        message: "Civisterial forbids sessionStorage; keep results in React state only.",
      },
      {
        object: "document",
        property: "cookie",
        message: "Civisterial forbids cookies.",
      },
    ],
  },
};
