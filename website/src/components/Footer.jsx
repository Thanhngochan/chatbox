import { profile } from "../config.js";

export default function Footer() {
  return (
    <footer className="footer">
      <div className="container footer__inner">
        <span>© {new Date().getFullYear()} {profile.name}</span>
        <span>Property sales · Rentals · Logistics</span>
      </div>
    </footer>
  );
}
