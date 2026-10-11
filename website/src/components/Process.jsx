const steps = [
  ["Tell me what you need", "Send a message on WhatsApp, WeChat or email, or ask the chat assistant on this page."],
  ["Free consultation", "We talk through your goals, budget and timeline, with no obligation."],
  ["A clear plan", "You get options, honest pricing and the next steps written down."],
  ["Done, together", "I handle viewings, negotiations, contracts or moving logistics until the job is finished."],
];

export default function Process() {
  return (
    <section className="section" id="process">
      <div className="container">
        <p className="eyebrow">How it works</p>
        <h2>Simple from first message to keys in hand</h2>
        <ol className="steps">
          {steps.map(([title, text], i) => (
            <li className="step" key={title}>
              <span className="step__num">{i + 1}</span>
              <h3>{title}</h3>
              <p>{text}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
