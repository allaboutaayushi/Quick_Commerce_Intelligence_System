# RevQ – Quick Commerce Intelligence System

A lightweight quick-commerce intelligence platform that consolidates product data across Blinkit, Zepto, and Instamart into a unified product identity model.

The system ingests marketplace data, resolves cross-platform product identities, stores historical pricing and availability snapshots, and exposes a React-based dashboard backed by an Express API.

---

## Overview

Quick-commerce platforms often list the same product with different naming conventions, packaging formats, and metadata. This project addresses that challenge by creating a canonical product identity layer that enables meaningful comparison across platforms.

Key capabilities include:

- Cross-platform product matching
- Canonical SKU generation
- Historical price and availability tracking
- Unified product intelligence API
- Interactive React-based product detail dashboard

---

## Features

### Product Identity Resolution

Products from Blinkit, Zepto, and Instamart are normalized into a single canonical representation using:

- Product type detection
- Flavor and variant extraction
- Weight normalization
- Deterministic SKU generation

Example:

text protein_bar__chocolate_chunk_nuts__60 

This allows equivalent products across platforms to be mapped into a single product record while preserving platform-specific listings.

---

### Market Intelligence

The platform provides:

- Current price comparison
- Availability tracking
- Discount analysis
- Platform-level listing information
- Historical snapshot storage

---

### Data Pipeline

The ingestion layer:

1. Reads marketplace scrape files
2. Extracts structured product attributes
3. Generates canonical identities
4. Stores platform listings
5. Records price and availability snapshots

Data Sources:

- Blinkit
- Zepto
- Instamart

---

## Tech Stack

### Frontend

- React
- Vite

### Backend

- Node.js
- Express.js

### Data Processing

- Python
- SQLite

### Architecture

- REST APIs
- Canonical Product Modeling
- Snapshot-Based Historical Tracking

---

## Project Structure

text RevQ/ ├── app/ │   ├── frontend (React + Vite) │   └── backend (Express API) │ ├── ingest/ │   └── Python ingestion pipeline │ ├── data/ │   ├── blinkit_sample.json │   ├── zepto_sample.json │   └── instamart_sample.json │ └── database/     └── SQLite 

---

## Run

https://quickcommerceintelligencesystem-mlbk8ybw7mhtgicvdse7qo.streamlit.app

---

## Design Decisions

### Why Canonical Product Identity?

Different platforms frequently represent identical products with slightly different naming conventions.

By separating:

- Canonical Products
- Platform Listings

the system can support accurate comparisons while preserving source-specific information.

### Why SQLite?

SQLite provides:

- Zero configuration
- Fast local development
- Simple portability

making it suitable for rapid prototyping and take-home exercises.

### Why Deterministic Matching?

The matching logic is intentionally transparent and explainable.

Rather than relying on opaque heuristics, normalization rules are visible, auditable, and easy to improve over time.

---

## Current Limitations

- Matching rules are handcrafted for the sample dataset.
- Pack count is not modeled separately.
- Historical trend visualization is not yet implemented.
- API does not include authentication or pagination.
- SQLite access is optimized for local development rather than production workloads.

---

## Future Improvements

- Confidence scoring for product matching
- Human review workflow for ambiguous products
- Price history visualizations
- Automated data quality validation
- Materialized latest-price views
- Comprehensive unit and integration testing
- Production-grade database layer

---

## Author

Aayushi Pandey

Full-Stack Developer & AI Engineer passionate about building products that don't just live in repositories—they solve real-world problems and create meaningful value for users.
