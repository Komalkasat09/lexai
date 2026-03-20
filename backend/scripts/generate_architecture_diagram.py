"""
Generate System Architecture Diagram for LexAI
Creates a professional PNG visualization of the 7-stage pipeline
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
fig, ax = plt.subplots(1, 1, figsize=(14, 10))
ax.set_xlim(0, 10)
ax.set_ylim(0, 12)
ax.axis('off')

# Title
ax.text(5, 11.5, 'LexAI System Architecture: 7-Stage Pipeline', 
        ha='center', va='top', fontsize=18, fontweight='bold')

# Color scheme
color_input = '#E8F4F8'
color_retrieval = '#B3E5FC'
color_processing = '#81D4FA'
color_middleware = '#4FC3F7'
color_generation = '#29B6F6'
color_gating = '#039BE5'
color_output = '#0277BD'

def add_box(ax, x, y, width, height, text, color, fontsize=10, fontweight='normal'):
    """Add a colored box with text"""
    box = FancyBboxPatch((x - width/2, y - height/2), width, height,
                         boxstyle="round,pad=0.1", 
                         edgecolor='black', facecolor=color, linewidth=2)
    ax.add_patch(box)
    ax.text(x, y, text, ha='center', va='center', fontsize=fontsize, 
            fontweight=fontweight, wrap=True)

def add_arrow(ax, x1, y1, x2, y2, label=''):
    """Add arrow between boxes"""
    arrow = FancyArrowPatch((x1, y1), (x2, y2),
                           arrowstyle='->', mutation_scale=25, linewidth=2.5, color='black')
    ax.add_patch(arrow)
    if label:
        mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(mid_x + 0.3, mid_y, label, fontsize=8, style='italic', 
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))

# Stage 1: Input
add_box(ax, 5, 10.5, 3, 0.6, 'Legal Question (English/Hindi)', color_input, fontsize=11, fontweight='bold')

# Arrow
add_arrow(ax, 5, 10.2, 5, 9.8)

# Stage 2: Query Classification & Encoding
add_box(ax, 5, 9.3, 3.5, 0.8, 'Query Classification (7 types)\n+ Dense & Sparse Encoding', 
        color_retrieval, fontsize=9, fontweight='bold')

# Arrow
add_arrow(ax, 5, 8.9, 5, 8.3)

# Stage 3: Parallel Retrieval from 3 Collections
add_box(ax, 2, 7.5, 2, 1.2, 'Bare Acts\n(500+ sections)\nDense + BM25', 
        color_retrieval, fontsize=8)
add_box(ax, 5, 7.5, 2, 1.2, 'Case Law\n(10k+ judgments)\nDense + BM25', 
        color_retrieval, fontsize=8)
add_box(ax, 8, 7.5, 2, 1.2, 'Amendments &\nOverruling Map\n(80+ records)', 
        color_retrieval, fontsize=8)

add_arrow(ax, 4, 8.3, 2.5, 8.1, 'RRF\nFusion')
add_arrow(ax, 5, 8.3, 5, 8.1)
add_arrow(ax, 6, 8.3, 7.5, 8.1)

# Arrow down
add_arrow(ax, 2, 6.9, 3.5, 6.3)
add_arrow(ax, 5, 6.9, 5, 6.3)
add_arrow(ax, 8, 6.9, 6.5, 6.3)

# Stage 4: Cross-Encoder Reranking
add_box(ax, 5, 5.8, 3.5, 0.8, 'Cross-Encoder Reranking\n(MS-MARCO model, top-5)', 
        color_processing, fontsize=9, fontweight='bold')

# Arrow
add_arrow(ax, 5, 5.4, 5, 4.9)

# Stage 5: Transition Classifier Middleware
add_box(ax, 5, 4.4, 3.8, 0.8, 'Transition Classifier Middleware\n(IPC→BNS, CrPC→BNSS)', 
        color_middleware, fontsize=9, fontweight='bold')

# Arrow
add_arrow(ax, 5, 4, 5, 3.4)

# Stage 6: LLM Generation
add_box(ax, 5, 2.9, 3.5, 0.8, 'LLM Generation\n(Groq Llama-3.3-70b, temp=0, seed=42)', 
        color_generation, fontsize=9, fontweight='bold')

# Arrow
add_arrow(ax, 5, 2.5, 5, 1.9)

# Stage 7: Confidence Gating & Output
add_box(ax, 5, 1.4, 3.8, 0.8, 'Confidence Gating\n(high=0.75, medium=0.60)', 
        color_gating, fontsize=9, fontweight='bold')

# Arrow
add_arrow(ax, 5, 1, 5, 0.4)

# Final Output
add_box(ax, 5, -0.2, 3, 0.6, 'Answer + Citations ± Abstention', 
        color_output, fontsize=10, fontweight='bold')

# Add side annotations
ax.text(0.2, 9.3, 'Input', fontsize=9, fontweight='bold', style='italic')
ax.text(0.2, 7.5, 'Retrieval\nStage 1', fontsize=9, fontweight='bold', style='italic')
ax.text(0.2, 5.8, 'Retrieval\nStage 2', fontsize=9, fontweight='bold', style='italic')
ax.text(0.2, 4.4, 'Middleware', fontsize=9, fontweight='bold', style='italic')
ax.text(0.2, 2.9, 'Generation', fontsize=9, fontweight='bold', style='italic')
ax.text(0.2, 1.4, 'Gating', fontsize=9, fontweight='bold', style='italic')
ax.text(0.2, -0.2, 'Output', fontsize=9, fontweight='bold', style='italic')

# Add legend for collections (bottom right)
legend_y = 0.5
ax.text(9.5, legend_y + 1.5, '📊 Collections:', fontsize=10, fontweight='bold', ha='right')
ax.text(9.5, legend_y + 0.8, '• ChromaDB (persistent)', fontsize=8, ha='right')
ax.text(9.5, legend_y + 0.3, '• 4 indexed collections', fontsize=8, ha='right')
ax.text(9.5, legend_y - 0.2, '• Multilingual embeddings', fontsize=8, ha='right')

plt.tight_layout()
plt.savefig('/Users/komalkasat09/legal-website/backend/evaluation/results/figures/figure1_system_architecture.png', 
            dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
print('✅ System architecture diagram saved: figure1_system_architecture.png')
plt.close()

# Also create a detailed component diagram
fig, ax = plt.subplots(1, 1, figsize=(14, 10))
ax.set_xlim(0, 10)
ax.set_ylim(0, 12)
ax.axis('off')

ax.text(5, 11.5, 'LexAI Component Architecture & Data Flow', 
        ha='center', va='top', fontsize=18, fontweight='bold')

# Left column: Data sources
ax.text(1.5, 10.5, 'DATA SOURCES', fontsize=11, fontweight='bold', ha='center',
        bbox=dict(boxstyle='round,pad=0.5', facecolor='#FFE0B2', alpha=0.8))

add_box(ax, 1.5, 9.5, 2, 0.6, 'India Code\n(Official Gazette)', '#FFCC80', fontsize=8)
add_box(ax, 1.5, 8.5, 2, 0.6, 'HuggingFace\nDataset', '#FFCC80', fontsize=8)
add_box(ax, 1.5, 7.5, 2, 0.6, 'Indian Kanoon\n(Live Scraping)', '#FFCC80', fontsize=8)

# Central column: Storage
ax.text(5, 10.5, 'STORAGE LAYER', fontsize=11, fontweight='bold', ha='center',
        bbox=dict(boxstyle='round,pad=0.5', facecolor='#B3E5FC', alpha=0.8))

add_box(ax, 5, 9.2, 2.5, 0.6, 'ChromaDB\n(Persistent)', '#81D4FA', fontsize=9, fontweight='bold')
add_box(ax, 3.5, 7.8, 1.3, 0.8, 'bare_acts', '#4FC3F7', fontsize=8)
add_box(ax, 5, 7.8, 1.3, 0.8, 'case_law', '#4FC3F7', fontsize=8)
add_box(ax, 6.5, 7.8, 1.3, 0.8, 'amendments', '#4FC3F7', fontsize=8)
add_box(ax, 4.3, 6.3, 1.4, 0.8, 'overruling_map', '#4FC3F7', fontsize=7)

# Connect data sources to storage
for y in [9.5, 8.5, 7.5]:
    add_arrow(ax, 2.5, y, 3.75, 8.8)

# Right column: Processing pipeline
ax.text(8.5, 10.5, 'PROCESSING PIPELINE', fontsize=11, fontweight='bold', ha='center',
        bbox=dict(boxstyle='round,pad=0.5', facecolor='#C8E6C9', alpha=0.8))

add_box(ax, 8.5, 9.2, 2.5, 0.6, 'Query Parser\n& Classifier', '#81C784', fontsize=8)
add_box(ax, 8.5, 8, 2.5, 0.8, 'Hybrid Retriever\n(Dense+Sparse+RRF)', '#66BB6A', fontsize=8)
add_box(ax, 8.5, 6.8, 2.5, 0.8, 'Cross-Encoder\nReranker', '#4CAF50', fontsize=8)
add_box(ax, 8.5, 5.6, 2.5, 0.8, 'Transition\nClassifier', '#388E3C', fontsize=8)

# Connect storage to processing
add_arrow(ax, 6.25, 8.2, 7.25, 8)
add_arrow(ax, 6.25, 8.2, 7.25, 6.8)
add_arrow(ax, 6.25, 8.2, 7.25, 5.6)

# Bottom: LLM and Output
ax.text(5, 4.5, 'GENERATION & OUTPUT', fontsize=11, fontweight='bold', ha='center',
        bbox=dict(boxstyle='round,pad=0.5', facecolor='#F8BBD0', alpha=0.8))

add_box(ax, 3, 3.3, 2.5, 0.8, 'Groq LLM\n(Deterministic)', '#EC407A', fontsize=8)
add_box(ax, 7, 3.3, 2.5, 0.8, 'Confidence\nGating', '#EC407A', fontsize=8)

add_arrow(ax, 8.5, 5.2, 4.25, 3.7)
add_arrow(ax, 4.25, 2.9, 7, 3.7)

add_box(ax, 5, 1.8, 3, 0.8, 'Final Answer\n(Text + Citations + Confidence)', '#C2185B', fontsize=9, fontweight='bold')

add_arrow(ax, 3, 2.9, 4, 2.2)
add_arrow(ax, 7, 2.9, 6, 2.2)

# Add technical specs
specs_y = 0.5
ax.text(0.5, specs_y + 0.5, 'TECHNICAL SPECS:', fontsize=9, fontweight='bold')
ax.text(0.5, specs_y, '• Embeddings: paraphrase-multilingual-MiniLM-L12-v2', fontsize=7)
ax.text(0.5, specs_y - 0.4, '• Cross-encoder: ms-marco-MiniLM-L-6-v2', fontsize=7)
ax.text(0.5, specs_y - 0.8, '• LLM: Groq Llama-3.3-70b (temp=0, seed=42)', fontsize=7)

plt.tight_layout()
plt.savefig('/Users/komalkasat09/legal-website/backend/evaluation/results/figures/system_architecture_detailed.png', 
            dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
print('✅ Detailed component diagram saved: system_architecture_detailed.png')

print('\n✅ ALL ARCHITECTURE DIAGRAMS GENERATED SUCCESSFULLY')
