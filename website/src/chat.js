// Opens the chat box if it has loaded; otherwise takes the visitor to the contact section.
export function openChat() {
  if (window.PropertyChat) window.PropertyChat.open();
  else document.getElementById("contact")?.scrollIntoView({ behavior: "smooth" });
}
