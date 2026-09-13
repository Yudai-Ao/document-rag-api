from app.services.document import extract_text, create_chunks


text = extract_text("sample.pdf")

chunks = create_chunks(
    text,
    source="sample.pdf"
    )

for chunk in chunks:
    print(chunk)