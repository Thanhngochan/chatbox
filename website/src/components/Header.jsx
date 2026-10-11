import { useState } from "react";
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
          onClick={() => setOpen(!open)}
        >
          {open ? <CloseIcon /> : <MenuIcon />}
        </button>
        <nav className={"nav" + (open ? " nav--open" : "")}>
          {links.map(([href, label]) => (
            <a key={href} href={href} onClick={() => setOpen(false)}>{label}</a>
          ))}
          <a href="#contact" className="btn btn--small" onClick={() => setOpen(false)}>Get in touch</a>
        </nav>
      </div>
    </header>
  );
}
