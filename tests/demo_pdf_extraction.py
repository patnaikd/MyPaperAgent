"""Demonstration script for PDF extraction functionality.

This script shows how to use the PDF extractor and metadata parser.
Run this after installing dependencies to test the PDF extraction pipeline.
"""
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.processing.pdf_extractor import PDFExtractor
from src.processing.metadata_parser import MetadataParser


def create_demo_pdf(output_path: Path) -> None:
    """Create a sample PDF for demonstration.

    Args:
        output_path: Where to save the PDF
    """
    import fitz

    # Create a sample academic paper
    content = """Attention Is All You Need

Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones,
Aidan N. Gomez, Łukasz Kaiser, Illia Polosukhin

Google Brain, Google Research, University of Toronto

Abstract

The dominant sequence transduction models are based on complex recurrent or
convolutional neural networks that include an encoder and a decoder. The best
performing models also connect the encoder and decoder through an attention
mechanism. We propose a new simple network architecture, the Transformer,
based solely on attention mechanisms, dispensing with recurrence and convolutions
entirely. Experiments on two machine translation tasks show these models to be
superior in quality while being more parallelizable and requiring significantly
less time to train. Our model achieves 28.4 BLEU on the WMT 2014 English-to-German
translation task, improving over the existing best results, including ensembles,
by over 2 BLEU. On the WMT 2014 English-to-French translation task, our model
establishes a new single-model state-of-the-art BLEU score of 41.8 after training
for 3.5 days on eight GPUs, a small fraction of the training costs of the best
models from the literature.

arXiv:1706.03762v5 [cs.CL] 6 Dec 2017

DOI: 10.48550/arXiv.1706.03762

Published in Advances in Neural Information Processing Systems (NeurIPS) 2017

1 Introduction

Recurrent neural networks, long short-term memory and gated recurrent neural
networks in particular, have been firmly established as state of the art approaches
in sequence modeling and transduction problems such as language modeling and
machine translation. Numerous efforts have since continued to push the boundaries
of recurrent language models and encoder-decoder architectures.

Attention mechanisms have become an integral part of compelling sequence modeling
and transduction models in various tasks, allowing modeling of dependencies without
regard to their distance in the input or output sequences. In all but a few cases,
however, such attention mechanisms are used in conjunction with a recurrent network.

In this work we propose the Transformer, a model architecture eschewing recurrence
and instead relying entirely on an attention mechanism to draw global dependencies
between input and output. The Transformer allows for significantly more parallelization
and can reach a new state of the art in translation quality after being trained for
as little as twelve hours on eight P100 GPUs.

2 Background

The goal of reducing sequential computation also forms the foundation of the Extended
Neural GPU, ByteNet and ConvS2S, all of which use convolutional neural networks as
basic building block, computing hidden representations in parallel for all input and
output positions. In these models, the number of operations required to relate signals
from two arbitrary input or output positions grows in the distance between positions.
"""

    doc = fitz.open()
    page = doc.new_page(width=612, height=792)  # Letter size

    # Add content with proper formatting
    rect = fitz.Rect(72, 72, 540, 720)  # 1 inch margins
    page.insert_textbox(rect, content, fontsize=10, fontname="helv")

    doc.save(output_path)
    doc.close()

    print(f"✓ Created demo PDF: {output_path}")


def demo_extraction() -> None:
    """Demonstrate PDF extraction and metadata parsing."""
    print("=" * 70)
    print("PDF Extraction and Metadata Parsing Demo")
    print("=" * 70)
    print()

    # Create demo PDF
    demo_pdf_path = Path(__file__).parent / "fixtures" / "demo_paper.pdf"
    demo_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    create_demo_pdf(demo_pdf_path)
    print()

    # Initialize extractor and parser
    extractor = PDFExtractor()
    parser = MetadataParser()

    # Extract from PDF
    print("Extracting content from PDF...")
    result = extractor.extract_from_file(demo_pdf_path)

    print(f"✓ Extraction method: {result['extraction_method']}")
    print(f"✓ Page count: {result['page_count']}")
    print(f"✓ Text length: {len(result['text'])} characters")
    print()

    # Show extracted text preview
    print("-" * 70)
    print("Extracted Text Preview (first 500 characters):")
    print("-" * 70)
    print(result["text"][:500])
    print("...")
    print()

    # Parse metadata
    print("-" * 70)
    print("Parsing Metadata:")
    print("-" * 70)
    metadata = parser.parse_metadata(result["text"], result["metadata"])

    print(f"Title: {metadata['title']}")
    print(f"Authors: {metadata['authors']}")
    print(f"Year: {metadata['year']}")
    print(f"DOI: {metadata['doi']}")
    print(f"arXiv ID: {metadata['arxiv_id']}")
    print(f"Journal: {metadata['journal']}")
    print()

    # Show abstract
    if metadata["abstract"]:
        print("-" * 70)
        print("Abstract:")
        print("-" * 70)
        print(metadata["abstract"])
        print()

    # Clean up (optional)
    # demo_pdf_path.unlink()

    print("=" * 70)
    print("Demo Complete!")
    print("=" * 70)
    print()
    print(f"Demo PDF saved at: {demo_pdf_path}")
    print("You can use this PDF for testing the application.")


if __name__ == "__main__":
    try:
        demo_extraction()
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
