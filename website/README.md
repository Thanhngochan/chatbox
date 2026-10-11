# Megan Goh website

The public website for Megan Goh: consulting on buying, selling and renting homes, and logistics.
Built with React + Vite. Responsive for phones (< 640px), tablets/iPad (640–1023px) and laptops (≥ 1024px).
The chat box from this repository (`../widget/property-chat.js`) floats in the bottom-right corner.

No Figma file was provided, so the design was made directly in React. If a Figma design arrives later,
the sections in `src/components/` map one-to-one to page sections and can be restyled in `src/styles.css`.

## Project structure

```
website/
  index.html            Page shell
  public/               Static files (favicon; add Megan's photo and WeChat QR here)
  src/
    main.jsx            Entry point
    App.jsx             Page layout: which sections appear, in order
    config.js           Megan's name, contacts and the chat server address
    chat.js             openChat() used by buttons
    styles.css          All styles; breakpoints at 640, 768, 1024 and 1280px
    components/         One file per section (Header, Hero, Services, About, Process, Contact, Footer, ChatWidget)
```

## Fill in Megan's details

Edit `src/config.js`: `email`, `whatsapp` (full international number, e.g. `+62 812 3456 7890`), `wechat` (WeChat ID)
and optionally `wechatQr` (put the QR image in `public/`). Empty fields show "Coming soon".
A photo can replace the "MG" circle in `src/components/About.jsx`.

## Run locally

```bash
cd website
npm install
npm run dev                                         # site only, no chat box
npm run lint                                        # check the code
npm run build                                       # production files in dist/
VITE_CHAT_SERVER=http://localhost:8000 npm run dev  # with the chat box (start the server first, see ../README.md)
```

## Publish online

**GitHub Pages (set up in this repo):**
1. Deploy the chat server (see "Deployment" in `../README.md`, e.g. Render or Railway) and note its HTTPS address.
2. In GitHub: Settings > Pages > Source: **GitHub Actions**.
3. Settings > Secrets and variables > Actions > Variables: add `CHAT_SERVER` = the chat server address.
4. Push to `main`. The site appears at `https://<user>.github.io/chatbox/`.
5. On the chat server, set `ALLOWED_ORIGINS` to the site's address (e.g. `https://<user>.github.io`).

**Vercel or Netlify (alternative):** import the repo, set the root directory to `website`, build command
`npm run build`, output `dist`, and add the `VITE_CHAT_SERVER` environment variable.
