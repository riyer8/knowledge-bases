# Product Vision

## Thesis

Don't describe this as "an AI assistant that answers questions about webpages." That's crowded.

Describe it as:

**An AI that remembers what you've learned.**

The webpage is the current context window. Your previous reading is long-term memory. The LLM is the reasoning layer connecting the two.

## The Shift

Instead of asking the user to save knowledge, the browser becomes the place where knowledge is automatically understood, connected, and remembered.

## Experience

You're reading a paper: *Scaling Laws for Neural Language Models…*

You open the extension and see:

**Ask about this page**

You can ask:

- "What does this actually mean?"
- "Explain this like I understand transformers but not scaling laws."
- "What assumptions are they making?"
- "How does this relate to the Chinchilla paper?"
- "Have I read anything before that contradicts this?"
- "What should I read next?"
- "Give me the 5 things I should remember from this."
- "Where in this paper is the evidence for this claim?"

### It remembers you, not just the webpage

Suppose you previously read 15 papers about transformers. The extension could say:

> This connects to something you've read before.
>
> You previously read *Attention Is All You Need* and *Scaling Laws for Neural Language Models*.
>
> The interesting connection is that this article assumes X, while the earlier paper emphasized Y.

Your knowledge graph becomes implicit rather than something you manually maintain.

## Four Modes

### 1. Understand

Current page only.

- "Explain this."
- "Summarize this section."
- "What does this diagram mean?"

### 2. Connect

Current page + your memory.

- "What have I read about this before?"
- "How does this relate to transformers?"
- "Have I encountered this person/company/concept?"

### 3. Learn

Turn browsing into a learning system.

- "Quiz me on this."
- "What am I misunderstanding?"
- "Give me 3 questions I should be able to answer after reading this."
- "Track the concepts I don't understand yet."

### 4. Explore

The assistant becomes your research partner.

- "What should I read next?"
- "Find gaps in my understanding."
- "What are the strongest arguments against this?"
- "Give me the rabbit holes worth going down."

## "Remember This"

You're reading something interesting. You highlight:

> Scaling laws predict model performance based on compute, dataset size, and model size…

A tiny floating button appears: **+ Remember**

Click it. The backend stores:

| Field | Example |
|---|---|
| Concept | Scaling Laws |
| Source | Scaling Laws for Neural Language Models |
| User note | Important for understanding model training |
| Related | Transformers, Compute scaling, Chinchilla, Language models |

You don't have to organize anything. The system automatically decides:

- what the concept is
- where it came from
- what it's related to
- whether you've seen it before
- how confident it is

That is your knowledge graph.

## Knowledge Graph Evolution

Today: Markdown A → Markdown B

Tomorrow:

```text
                Transformer
                    │
          ┌─────────┼──────────┐
          │         │          │
      Attention   Scaling    Tokenizer
          │         │          │
      Paper A    Paper B    Paper C
          │
     "You read this Aug 28"
```

Each node can have:

- Sources
- First encountered / last encountered
- Times referenced
- Related concepts
- Your notes
- Understanding score

## Architectural Roles

| Layer | Responsibility |
|---|---|
| Chrome | Eyes + interface — captures context |
| Python backend | Memory — stores, indexes, connects |
| LLM | Reasoning — answers using context + memory |
| Database | Long-term storage |

Eventually: Chrome, Safari, Desktop, Phone, PDF reader, Terminal, YouTube, Books — all feeding the same memory.
