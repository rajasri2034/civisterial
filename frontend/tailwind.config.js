/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        gov: {
          text: '#0b0c0c',
          secondary: '#505a5f',
          link: '#1d70b8',
          linkHover: '#003078',
          border: '#b1b4b6',
          panel: '#f3f2f1',
          navy: '#0B1F3A',
          green: '#00703c',
          greenHover: '#005a30',
          greenShadow: '#002d18',
          greyBtn: '#f3f2f1',
          greyBtnHover: '#dbdad9',
          greyShadow: '#929191',
          error: '#d4351c',
          focus: '#ffdd00',
          warningBg: '#fef7f1',
          warningBorder: '#f47738',
        },
      },
      fontFamily: {
        sans: [
          '"Public Sans"',
          '"Noto Sans Tamil"',
          '"Noto Sans Devanagari"',
          'system-ui',
          '-apple-system',
          'sans-serif',
        ],
      },
      maxWidth: {
        gov: '960px',
      },
      borderRadius: {
        none: '0px',
        gov: '2px',
      },
    },
  },
  plugins: [],
};
