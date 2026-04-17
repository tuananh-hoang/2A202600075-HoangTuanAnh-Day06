# data_pipeline/chunk.py
import json
from pathlib import Path

def process_markdown_to_chunks(raw_dir, output_file):
    chunks = []
    chunk_id_counter = 0
    
    for md_file in Path(raw_dir).glob("*.md"):
        # Extract doc_id from filename (remove extension)
        doc_id = md_file.stem
        
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Simple chunking - split by paragraphs
        paragraphs = content.split('\n\n')
        
        for chunk_index, para in enumerate(paragraphs):
            if para.strip():
                chunk_text = para.strip()
                chunks.append({
                    "doc_id": doc_id,
                    "filename": md_file.name,
                    "source_path": f"raw_data/{md_file.name}",
                    "chunk_index": chunk_index,
                    "section_title": "",
                    "section_chunk_index": 0,
                    "text": chunk_text,
                    "char_count": len(chunk_text)
                })
                chunk_id_counter += 1
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
    
    print(f"✅ Created {len(chunks)} chunks in {output_file}")
    print(f"📄 Processed {len(list(Path(raw_dir).glob('*.md')))} markdown files")

if __name__ == "__main__":
    process_markdown_to_chunks(
        "data_pipeline/raw_data",
        "data_pipeline/processed_data/chunks.jsonl"
    )
