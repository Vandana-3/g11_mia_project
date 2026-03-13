# Technical Rationale & Design Decisions

This document explains the "Why" behind the mathematical and architectural choices in the Renal Data Project pipeline.

## 1. Why Backcasting? (The Anchor Strategy)
**The Problem**: We had 100% ground-truth patient data for 2021, but zero patient data for 2016–2020.
**The Solution**: Instead of "guessing" history from scratch, we use 2021 as a **Truth Anchor**. 
- **Rationale**: A clinic's volume doesn't usually change by 500% overnight. By starting with the 2021 volume and "backcasting," we ensure the synthetic history is anchored in reality and maintains the geographic signature of the clinic.

## 2. Why Gamma (γ)? (The Sensitivity Engine)
**The Problem**: How much should historical census changes impact patient visits?
**The Solution**: We estimate a **Deprivation Coefficient (Gamma)** using a regression on the 2021 observed data.
- **Rationale**: Different clinics respond differently to socio-economics. By *learning* Gamma from the 2021 data (Regression: `Volume ~ OMI`), we ensure the synthetic history respects the real-world correlation already present in the clinic's environment.

## 3. Why Poisson Distribution? (The Noise Logic)
**The Problem**: Real-world data isn't perfectly linear; it has variance.
**The Solution**: We use the Poisson distribution to generate final integer counts.
- **Rationale**: Patient visits are "count data." The Poisson distribution is the statistical standard for modeling events (like clinic visits) because it ensures integers (you can't have 1.5 patients) and naturally handles the variance of low-volume areas.

## 4. Why Linear Interpolation? (The Gap Bridge)
**The Problem**: The ON-Marg census only happens every 5 years (2016 and 2021). We need features for 2017, 2018, 2019, and 2020.
**The Solution**: We use a simple linear progression between 2016 and 2021.
- **Rationale**: Socio-economic variables in a neighborhood (like "Instability" or "Deprivation") typically evolve slowly. A linear bridge is the most conservative and statistically sound way to simulate a steady trend between two known snapshots.

## 5. Why a "Hybrid" 2016?
**The Choice**: Labeling 2016 as a Hybrid year (Real Features / Synthetic Target).
**Rationale**: We have the actual **real 2016 census data**. It is far better to use these real observed features for training the ML model than to interpolate them. This gives the model a second "Real" endpoint for features, even if the target (volume) is simulated.
