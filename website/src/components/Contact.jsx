import { useState } from "react";
import { profile } from "../config.js";
import { MailIcon, WhatsAppIcon, WeChatIcon } from "./Icons.jsx";

const SOON = "Coming soon";

function CopyButton({ value }) {
  const [done, setDone] = useState(false);
  return (
    <button
      type="button"
      className="btn btn--small btn--ghost"
      onClick={() => {
        navigator.clipboard?.writeText(value).then(() => {
          setDone(true);
          setTimeout(() => setDone(false), 1500);
        });
      }}
    >
      {done ? "Copied" : "Copy ID"}
    </button>
  );
}

export default function Contact() {
  const waDigits = profile.whatsapp.replace(/[^\d]/g, "");
  return (
    <section className="section section--dark" id="contact">
      <div className="container">
        <p className="eyebrow">Contact</p>
        <h2>Let's talk about your next move</h2>
        <p className="lead">Reach Megan directly on the channel you prefer.</p>
        <div className="grid grid--3">
          <div className="contact">
            <div className="contact__icon"><MailIcon /></div>
            <h3>Email</h3>
            <p>{profile.email || SOON}</p>
            {profile.email && <a className="btn btn--small" href={`mailto:${profile.email}`}>Send email</a>}
          </div>
          <div className="contact">
            <div className="contact__icon"><WhatsAppIcon /></div>
            <h3>WhatsApp / Phone</h3>
            <p>{profile.whatsapp || SOON}</p>
            {waDigits && (
              <div className="contact__actions">
                <a className="btn btn--small" href={`https://wa.me/${waDigits}`} target="_blank" rel="noopener noreferrer">Chat on WhatsApp</a>
                <a className="btn btn--small btn--ghost" href={`tel:+${waDigits}`}>Call</a>
              </div>
            )}
          </div>
          <div className="contact">
            <div className="contact__icon"><WeChatIcon /></div>
            <h3>WeChat</h3>
            <p>{profile.wechat ? `ID: ${profile.wechat}` : SOON}</p>
            {profile.wechatQr && <img className="contact__qr" src={profile.wechatQr} alt="WeChat QR code" />}
            {profile.wechat && <CopyButton value={profile.wechat} />}
          </div>
        </div>
      </div>
    </section>
  );
}
