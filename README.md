# Real-estate advice chat box

> Hướng dẫn chạy website Megan Goh cùng chat box (tiếng Việt): [HUONG-DAN.md](HUONG-DAN.md)

An AI chat box (powered by Claude) that gives real-estate advice and **can be embedded in any personal website with a single `<script>` tag**.

- Searches listings by criteria (area, price, bedrooms, legal status...) and shows them as cards.
- Answers questions about projects and the home-buying process with **RAG**: for every question, the most relevant chunks of your documents (`projects.md`, `buying_faq.md`, the `docs/` folder) are retrieved and given to Claude, so it does not make things up.
- Understands Vietnamese typed without accents and common abbreviations ("thu tuc sang ten", "q7", "thu duc").
- Streams the answer as it is written, adapts to phone screens, and its CSS never touches the host website.

The code, comments and docs are in English. The sample data and the texts shown to visitors are in Vietnamese, because the target customers are Vietnamese; Claude answers in the customer's language.

```
server/            FastAPI backend: calls Claude and keeps the API key secret
  app.py           API, system prompt, tools
  knowledge.py     RAG: chunking and BM25 search
  listings.py      Loading and filtering listings
widget/            property-chat.js, the script embedded in websites
demo/              Sample website with the chat box embedded
website/           Megan Goh's React website, with the chat box embedded (see website/README.md)
projects.md, buying_faq.md, listings.csv   Data (replace with your real data)
docs/              Drop extra .md/.txt files here and the chat box searches them
tests/             Automated tests (use a fake Claude, no API cost)
rag_chatbot.ipynb  RAG learning notebook (embeddings + Chroma)
```

## Run it locally

```bash
cd server
pip install -r requirements.txt
cp .env.example .env        # then paste your ANTHROPIC_API_KEY into .env
uvicorn app:app --env-file .env --reload --port 8000
```

Open <http://localhost:8000> to see the demo page with the chat box.

## Embed it in your website

Once the server is online (see Deployment), paste this before the `</body>` tag of your website:

```html
<script src="https://chat.your-domain.com/widget.js"
        data-title="Tư vấn nhà đất"
        data-color="#0f766e"
        data-contact="tel:0900000000"
        defer></script>
```

Works with plain HTML, WordPress (any header/footer code plugin), Wix/Webflow (custom code), Next.js/React (`<Script>`)...

### Options

| Attribute | Meaning | Default |
|---|---|---|
| `data-api` | Server address, if different from where `widget.js` is served | taken from `src` |
| `data-title` / `data-subtitle` | Title and subtitle | "Tư vấn bất động sản" |
| `data-color` | Main color | `#0f766e` |
| `data-position` | `right` or `left` | `right` |
| `data-greeting` | First greeting message | built in |
| `data-suggestions` | Suggested questions, separated by `\|` | 3 samples |
| `data-contact` / `data-contact-label` | Contact link (`tel:`, Zalo, Messenger) | hidden |
| `data-open` | `true` to open the chat on page load | `false` |
| `data-lang` | `en` for English interface texts | Vietnamese |

The other interface texts are in the `TEXT` object at the top of `widget/property-chat.js`.

### Control it from your website

```js
PropertyChat.open();
PropertyChat.close();
PropertyChat.ask("Có căn nào dưới 2 tỷ không?"); // open and ask right away
```

Example "Ask about this listing" button on a listing page: `onclick="PropertyChat.ask('Cho mình xem chi tiết tin T003')"`.

## How the chat box answers (RAG)

1. **Retrieval**: documents are split into chunks by `##` section (long sections are split further). For each question the server finds the most relevant chunks with BM25, matching Vietnamese without accents and favouring two-word phrases ("sổ hồng", "đặt cọc"). Short follow-ups ("còn phí quản lý thì sao?") are combined with the previous question so the right chunks are found.
2. **Augmentation**: the retrieved chunks are attached to the question sent to Claude.
3. **Generation**: Claude answers only from those chunks. If they are not enough, Claude calls the `search_documents` tool to search again with a different query; for listings it calls `search_listings` to filter exactly by price, area, bedrooms...

The search is pure Python and needs no embedding model, so the server stays small and runs on free hosting tiers. Once the documents reach thousands of pages, you can switch to semantic search as in `rag_chatbot.ipynb` (only `server/knowledge.py` needs to change).

## Use your real data

- `listings.csv`: keep the column names, add or remove rows freely. Opening and saving it in Excel is fine; prices can be written `3.2` or `3,2`, and malformed rows are skipped with a warning. `type` is one of `apartment`, `townhouse`, `land`.
- `projects.md`, `buying_faq.md`: free text organised in `##` sections, one topic per section.
- Other documents: put `.md`/`.txt` files in the `docs/` folder (see `docs/README.md`).
- Restart the server after changing the data. `GET /api/health` shows how many listings and document chunks were loaded.

## Server settings (`server/.env`)

| Variable | Meaning | Default |
|---|---|---|
| `ANTHROPIC_API_KEY` | Claude API key (required, server side only) | none |
| `CLAUDE_MODEL` | Model | `claude-sonnet-5-5` |
| `CLAUDE_EFFORT` | Thinking effort `low`/`medium`/`high` | `low` |
| `ALLOWED_ORIGINS` | Websites allowed to embed the chat box, comma separated | `*` |
| `RATE_LIMIT_PER_MINUTE` | Maximum questions per minute per IP | `15` |
| `RAG_CHUNKS` | Document chunks given to Claude per question | `4` |

In production, set `ALLOWED_ORIGINS` to your own domain so other websites cannot use your API key.
The server enables `fallbacks: "default"`: if the safety filter refuses by mistake, the API answers with a fallback model.

## Tests

```bash
pip install -r requirements-dev.txt
python -m playwright install chromium   # first time only
python -m pytest tests
```

The tests run the real server against a fake Claude, so no API key is needed. They cover listing filters, document search (with and without accents), the API (Claude errors, lost connection, refusals, invalid tool parameters, rate limiting, CORS, missing API key) and the widget in Chromium (desktop, phone, embedded on another origin, HTML injection). GitHub Actions runs them on every pull request.

## Deployment

A `Dockerfile` is included; it runs on Render, Railway, Fly.io, Google Cloud Run...

```bash
docker build -t property-chat .
docker run -p 8000:8000 --env-file server/.env property-chat
```

On those services: point to the repo, choose the Dockerfile build, and add the `ANTHROPIC_API_KEY` and `ALLOWED_ORIGINS` environment variables. The server must use HTTPS if your website does.

## API

`POST /api/chat` takes `{"messages": [{"role": "user", "content": "..."}]}` (the conversation history, up to 20 messages) and returns Server-Sent Events:
`text` (pieces of the answer), `listings` (listings to draw as cards), `error`, `done`.
`GET /api/health` checks the server.
