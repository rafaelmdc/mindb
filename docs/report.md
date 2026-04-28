You are helping me write a concise LaTex project report (around 8–12 pages, target ~10 pages) about my microbiome database project called ORDINA.

Your job is to generate the full LaTex source for the report, with a clean academic/professional structure, but not overly formal or unnecessarily long. The document should read like a compact final project report that explains the motivation, design logic, implementation, and resulting platform.

Important constraints:
- Write in clear English.
- Keep it concise but complete.
- Do not make up fake results, fake metrics, or fake screenshots.
- Where screenshots/images are needed, insert clear figure placeholders and descriptive captions, and comment where I should later add the real file paths.
- The report should be structured so that I can compile it directly after replacing image placeholders.
- Use standard LaTex packages only.
- Use a clean report/article style. `article` is preferred unless you think another class is clearly better.
- Include a title page, table of contents, and numbered sections.
- Do not overdo citations. If no bibliography is provided, keep the document mostly self-contained and avoid inventing references.
- The tone should be that of a computer science / bioinformatics MSc project report.

Context about the project
The project is a microbiome literature curation and exploration platform called ORDINA. Its purpose is to help centralize and organize microbiome-related findings from the scientific literature, especially disease–microorganism associations, in a way that is structured, reproducible, and explorable.

Core project logic and motivation:
- Microbiome studies are scattered across many papers.
- Findings are often difficult to compare because papers differ in cohort definitions, metadata reporting, taxa naming, and how results are presented.
- A centralized database helps store evidence in a structured way.
- The goal is not just to collect papers, but to model the relationships between studies, groups, comparisons, organisms, and findings in a way that supports later querying and visualization.
- The database is meant to support reproducible meta-analysis and better exploration of microbiome–disease relationships.
- A key design decision is to preserve study context rather than flatten everything into simple organism lists.
- The project also supports qualitative findings such as “increased in disease” / “decreased in disease” when exact numeric values are not available.
- Quantitative values, when reported directly in text or tables, can also be stored.
- Diversity metrics such as alpha/beta diversity can also be represented.
- The broader aim is to create a useful and extensible platform for future microbiome evidence integration and exploration.

Implementation context:
- The platform uses Django for the web framework.
- PostgreSQL is used for the database.
- Bootstrap is used for the frontend/UI.
- Graph/network payloads are built in Python and rendered interactively in the browser.
- The website provides a browser/explorer for the stored database contents.
- The system includes an admin/import-oriented workflow for bringing curated literature data into the database.
- The implementation is still an early but functional prototype, focused on correctness of structure and extensibility rather than polished production deployment.

Taxon Bridge context:
- Taxon Bridge is a supporting tool/library created to help resolve organism names and taxonomy-related issues.
- Its role is to help bridge raw organism names found in the literature with a cleaner and more structured taxonomy-aware representation.
- It was developed because taxonomic names in papers can be inconsistent, incomplete, outdated, or reported at different taxonomic ranks.
- It supports the main ORDINA platform by making organism handling more robust and by enabling future grouping/sorting/filtering by taxonomic lineage.
- In the report, Taxon Bridge should be presented as an important supporting component rather than the main project itself.

What the report must contain

1. Introduction
- Briefly introduce the microbiome field and the difficulty of comparing findings across the literature.
- Explain the motivation for creating ORDINA.
- State the project goals clearly.
- Emphasize centralization, structured curation, reproducibility, and exploration of microbiome–disease associations.

2. Problem and rationale
- Explain why existing literature is hard to compare directly.
- Mention heterogeneous study designs, subgroup definitions, taxonomic naming inconsistency, and inconsistent reporting of findings.
- Explain why a structured database is more useful than keeping notes or spreadsheets alone.
- Explain why preserving comparison context matters.

3. Conceptual design / data logic
- Present the conceptual logic of the platform.
- Explain that the model revolves around entities such as studies, groups/cohorts, comparisons, organisms, and findings.
- Explain qualitative findings and quantitative findings.
- Explain why comparisons are modeled explicitly.
- Explain the logic behind storing direction-of-change evidence.
- Mention that the system is intended to support later querying, browsing, and network-based interpretation.

4. Implementation
- Present the actual implementation choices.
- Explain the use of Django, PostgreSQL, Bootstrap, and the current graph rendering approach.
- Explain the role of the web interface.
- Explain the import/admin workflow at a high level.
- Keep this section practical and grounded in what was implemented.

5. Taxon Bridge
- Add a dedicated section presenting Taxon Bridge.
- Explain why it was needed.
- Explain its role in organism/taxonomy normalization or taxonomic bridging.
- Explain how it supports the main ORDINA platform.
- Make clear that this component improves the quality and future extensibility of the database.

6. Website / platform presentation
- Present the website itself.
- Describe what the user can do with it at a high level.
- Mention database browsing, structured exploration, and future potential for graph/network visualization.
- Mention all the admin capabilities (user management, schema, upload)
- Include screenshot placeholders for the website pages.

7. Current state, limitations, and future work
- Be honest that this is an early-stage but functional prototype.
- Mention that literature curation is labor-intensive.
- Mention that taxonomy resolution and metadata standardization remain challenging.
- Mention that future work could include more automated ingestion, richer taxonomy integration, broader literature coverage, and more advanced network visualization/analysis.

8. Conclusion
- Summarize the value of the project.
- Reinforce that ORDINA provides a structured foundation for centralized microbiome evidence integration and exploration.

Figures and placeholders
I will provide the screenshots later. For now:
- Insert figure environments with placeholder filenames.
- Use meaningful captions.
- Add LaTeX comments above each figure saying what screenshot should be inserted there.

At minimum, include placeholders for:
- A screenshot of the ORDINA website homepage or main interface
- A screenshot of the database browsing/exploration page
- A screenshot showing Taxon Bridge working
- Optionally a screenshot of an admin/import or graph-related view if it fits naturally

Formatting instructions
- Use sensible sectioning and subsectioning.
- Use paragraphs, not excessively long bullet lists.
- Bullet lists are acceptable only when they improve clarity.
- The document should feel like a student project report, not a publication manuscript.
- Keep the overall output compact enough for ~10 pages with a few figures.
- Add a short abstract.
- Add keywords if appropriate.
- Avoid overly inflated wording.

Output format
Return only the full LaTex source code in one block, ready to save as something like `mindb_report.tex`.

If needed, make reasonable assumptions from the project description above, but do not invent experimental results or unimplemented features.
