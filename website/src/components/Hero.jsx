import { profile } from "../config.js";
import { openChat } from "./ChatWidget.jsx";

export default function Hero() {
  return (
    <section className="hero" id="top">
      <div className="container hero__inner">
        <div className="hero__text">
          <p className="eyebrow">{profile.title}</p>
          <h1>Your trusted partner for homes and logistics</h1>
          <p className="lead">{profile.tagline}</p>
          <div className="hero__actions">
            <a href="#contact" className="btn">Book a consultation</a>
            <button type="button" className="btn btn--ghost" onClick={() => openChat()}>Ask a question</button>
          </div>
        </div>
        <div className="hero__card" aria-hidden="true">
          <div className="stat"><strong>Sell</strong><span>Pricing, marketing, negotiation</span></div>
          <div className="stat"><strong>Rent</strong><span>Tenants, landlords, contracts</span></div>
          <div className="stat"><strong>Move</strong><span>Freight, relocation, warehousing</span></div>
        </div>
      </div>
    </section>
  );
}
