// Everything about Megan that appears on the site lives here.
// Fill in the empty fields; anything left empty is shown as "coming soon".
export const profile = {
  name: "Megan Goh",
  title: "Property & Logistics Consultant",
  tagline: "Buy, sell or rent with confidence, and move what matters with ease.",

  // Contact details (left empty until Megan supplies them)
  email: "",          // e.g. "megan@example.com"
  whatsapp: "",       // full international number, e.g. "+62 812 3456 7890"
  wechat: "",         // WeChat ID, e.g. "megangoh88"
  wechatQr: "",       // optional: put the QR image in website/public/ and write its file name, e.g. "wechat-qr.png"
};

// Address of the chat box server (the FastAPI app in ../server), e.g. "https://chat.example.com".
// Set VITE_CHAT_SERVER when building, or write it here. Empty = no chat box.
export const chatServer = (import.meta.env.VITE_CHAT_SERVER || "").replace(/\/$/, "");
