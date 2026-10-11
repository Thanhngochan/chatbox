import { useEffect } from "react";
import { chatServer, profile } from "../config.js";

// Loads the chat box from ../widget/property-chat.js, served by the chat server at /widget.js.
// The widget draws itself in a Shadow DOM, so it never clashes with this site's CSS.
export default function ChatWidget() {
  useEffect(() => {
    if (!chatServer || document.getElementById("property-chat-script")) return;
    const s = document.createElement("script");
    s.id = "property-chat-script";
    s.src = chatServer + "/widget.js";
    s.defer = true;
    Object.assign(s.dataset, {
      title: `Chat with ${profile.name}`,
      subtitle: "AI assistant · replies 24/7",
      color: "#0f766e",
      greeting: "Hi! I can help you find a home to buy or rent, or answer questions about the process. What are you looking for?",
      lang: "en",
      suggestions: "Show me homes for rent|What does it cost to sell my house?|How do I plan a move?",
    });
    const wa = profile.whatsapp.replace(/[^\d]/g, "");
    if (wa) {
      s.dataset.contact = `https://wa.me/${wa}`;
      s.dataset.contactLabel = "WhatsApp Megan";
    }
    s.onerror = () =>
      console.error(`Chat box: could not load ${s.src}. Is the chat server running? (see HUONG-DAN.md)`);
    document.body.appendChild(s);
  }, []);
  return null;
}
