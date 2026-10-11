import { profile } from "../config.js";

export default function About() {
  return (
    <section className="section section--tint" id="about">
      <div className="container about">
        <div className="about__portrait" aria-hidden="true">
          {/* Replace with a photo: <img src="megan.jpg" alt="Megan Goh" /> after adding it to website/public/ */}
          <span>MG</span>
        </div>
        <div>
          <p className="eyebrow">About</p>
          <h2>Hi, I’m {profile.name}</h2>
          <p>
            I help families, investors and businesses make confident decisions about property and the
            logistics that come with it. Selling a home, finding the right rental or planning a move,
            you get one person who listens, explains every step clearly and stays with you until it is done.
          </p>
          <ul className="badges">
            <li>Personal, one-to-one service</li>
            <li>Clear, honest advice</li>
            <li>Quick replies on WhatsApp &amp; WeChat</li>
          </ul>
        </div>
      </div>
    </section>
  );
}
