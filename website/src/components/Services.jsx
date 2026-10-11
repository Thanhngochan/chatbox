import { HomeIcon, KeyIcon, TruckIcon } from "./Icons.jsx";

const services = [
  {
    icon: <HomeIcon />,
    title: "Buying & selling homes",
    text: "Honest market valuations, staging advice and skilled negotiation, so you buy at the right price or sell for what your home is worth.",
    points: ["Free property valuation", "Buyer matching & viewings", "Paperwork and handover support"],
  },
  {
    icon: <KeyIcon />,
    title: "Renting & leasing",
    text: "Whether you are a landlord looking for reliable tenants or a family looking for the right place, Megan handles the search and the details.",
    points: ["Tenant screening", "Fair rental contracts", "Short and long-term leases"],
  },
  {
    icon: <TruckIcon />,
    title: "Logistics consulting",
    text: "Practical advice on moving goods and people: from relocating your household to planning shipping and storage for your business.",
    points: ["Home & office relocation", "Freight and shipping planning", "Warehousing options"],
  },
];

export default function Services() {
  return (
    <section className="section" id="services">
      <div className="container">
        <p className="eyebrow">Services</p>
        <h2>How Megan can help</h2>
        <div className="grid grid--3">
          {services.map((s) => (
            <article className="card" key={s.title}>
              <div className="card__icon">{s.icon}</div>
              <h3>{s.title}</h3>
              <p>{s.text}</p>
              <ul className="ticks">
                {s.points.map((p) => <li key={p}>{p}</li>)}
              </ul>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
