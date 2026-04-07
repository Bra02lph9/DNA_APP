# 🧬 DNA Analyzer

DNA Analyzer is a high-performance full-stack bioinformatics application designed to analyze bacterial DNA sequences and identify biologically meaningful signals involved in gene expression.

The application integrates multiple genomic features to predict the most plausible coding regions.

---

## 🚀 Key Features

- ORF (Open Reading Frame) detection across all 6 reading frames  
- Start and stop codon identification  
- Sigma70 promoter detection (-35 / -10 regions)  
- Shine-Dalgarno sequence detection  
- Rho-independent transcription terminator detection  
- Biologically-informed scoring system to rank the most plausible ORFs  

---

## ⚡ Performance

- Capable of analyzing a complete bacterial genome (~5 million nucleotides)  
- Processing time: under 1 minute  
- Optimized using:
  - Cython  
  - Numba  
  - Parallel processing  
  - Chunking strategies  

---

## 🧬 ORF Detection

The application scans all six reading frames:

- 3 frames on the forward strand  
- 3 frames on the reverse complement  

Detection criteria:

- Start codons: ATG, GTG, TTG  
- Stop codons: TAA, TAG, TGA  
- Minimum protein length threshold to reduce false positives  

A biological filtering step is applied to retain only potentially coding ORFs.

---

## 📍 Promoter Detection

Detection of bacterial sigma70 promoters:

- -35 box: TTGACA  
- -10 box: TATAAT  

Criteria used:

- Mismatch tolerance  
- Biologically relevant spacing between boxes  
- Scoring system to rank detected promoters  

---

## 🔗 Shine-Dalgarno Detection

The Shine-Dalgarno sequence is a ribosome binding site located upstream of the start codon.

Consensus sequence:

- AGGAGG  

Constraints applied:

- Located 7–9 nucleotides upstream of the start codon  
- Automatically associated with detected ORFs  
- Filtering of biologically plausible sites  

---

## 🧪 Rho-independent Terminators

Characterized by:

- Palindromic sequence forming a hairpin structure  
- GC-rich region  
- Downstream poly-T tail  

The application detects these features to identify potential transcription terminators.

---

## 🧠 ORF Scoring System

Each ORF is evaluated based on multiple biological signals:

- Presence of promoter  
- Presence of Shine-Dalgarno sequence  
- Presence of terminator  
- Distance consistency between signals  
- ORF length and structure  

This allows prioritization of the most biologically plausible genes.

---

## 🖥️ User Interface

The interface allows:

- Uploading DNA sequences (FASTA format)  
- Visualization of detected features  
- Highlighting biological elements  
- Navigation between results  
- Selection and localization of specific signals  

---

## 🛠️ Tech Stack

- Backend: Python, Flask, BioPython  
- Optimization: Cython, Numba  
- Task Queue: Celery, Redis  
- Database: MongoDB  
- Deployment: Docker  
- Frontend: React, Tailwind CSS  

---

## 🎯 Project Goal

This project demonstrates the integration of bioinformatics methods into a modern web application.

It aims to combine biological relevance with high-performance computing to analyze genomic data efficiently and interactively.

---
# Screenshots
![Interface](screnshots/uu.png)
![Sequence Viewer](screnshots/aa.png)
![Results](screnshots/zz.png)
![Results](screnshots/ee.png)
![Results](screnshots/rr.png)
![Results](screnshots/tt.png)
![Results](screnshots/yy.png)

---

