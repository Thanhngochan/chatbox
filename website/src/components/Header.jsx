import { useEffect, useState } from "react";
import { profile } from "../config.js";
import { MenuIcon, CloseIcon } from "./Icons.jsx";

const links = [
  ["#services", "Services"],
  ["#about", "About"],
  ["#process", "How it works"],
  ["#contact", "Contact"],
];

export default function Header() {
  const [open, setOpen] = useState(false);

  // Close the phone/tablet menu with Escape, or when the window grows to laptop width
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => e.key === "Escape" && setOpen(false);
    const wide = window.matchMedia("(min-width: 1024px)");
    const onWide = () => wide.matches && setOpen(false);
    window.addEventListener("keydown", onKey);
    wide.addEventListener("change", onWide);
    return () => {
      window.removeEventListener("keydown", onKey);
      wide.removeEventListener("change", onWide);
    };
  }, [open]);
  return (
    <header className="header">
      <div className="container header__inner">
        <a href="#top" className="brand" onClick={() => setOpen(false)}>
          <span className="brand__mark">MG</span>
          <span className="brand__name">{profile.name}</span>
        </a>
        <button
          className="header__toggle"
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          aria-controls="site-nav"
          onClick={() => setOpen(!open)}
        >
          {open ? <CloseIcon /> : <MenuIcon />}
        </button>
        <nav id="site-nav" className={"nav" + (open ? " nav--open" : "")}>
          {links.map(([href, label]) => (
            <a key={href} href={href} onClick={() => setOpen(false)}>{label}</a>
          ))}
          <a href="#contact" className="btn btn--small" onClick={() => setOpen(false)}>Get in touch</a>
        </nav>
      </div>
    </header>
  );
}
