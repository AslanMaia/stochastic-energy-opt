# stochastic-energy-opt
Stochastic Modeling and Optimization of the Operation of Energy Communities with Hybrid Storage

# Stochastic Energy Management for Residential Energy Communities

This repository contains the implementation of a two-stage stochastic 
optimization model for the operational management of residential energy 
communities integrating photovoltaic generation and hybrid energy storage 
(battery + hydrogen).

## Overview

Energy communities are groups of households that share local renewable 
generation and storage resources. Managing these systems efficiently is 
challenging because both solar generation and electricity demand are 
uncertain — they vary day to day in ways that cannot be perfectly predicted 
in advance.

This project addresses that challenge by formulating the management problem 
as a **Mixed-Integer Linear Program (MILP)** under uncertainty. Rather than 
optimizing for a single predicted scenario, the model considers multiple 
plausible scenarios simultaneously and finds the operating strategy that 
minimizes expected energy cost across all of them.

## The Two-Stage Structure

The model follows a classical two-stage stochastic programming structure:

- **First stage** — decisions made *before* uncertainty is revealed, such as 
  the charge/discharge schedule of the storage systems.
- **Second stage** — decisions made *after* the scenario is revealed, such as 
  how much power to draw from or sell back to the grid, given what generation 
  and demand actually occurred.

This structure reflects real-world operation: a community energy manager must 
commit to certain decisions (e.g., when to charge batteries) before knowing 
exactly how much sun there will be or how much energy residents will consume.

## Key Metrics

The model is evaluated using the **Value of the Stochastic Solution (VSS)** — 
the cost difference between solving the problem with explicit uncertainty 
versus assuming a single average scenario. A high VSS indicates that 
accounting for uncertainty leads to meaningfully better decisions.

## Technical Stack

- **Language:** Python
- **Optimization framework:** Pyomo
- **Solver:** HiGHS / Gurobi
- **Data handling:** pandas

## Research Context

This project is developed as an undergraduate research project (*Iniciação 
Científica*) funded by **FAPESP**, at the Center for Energy Planning and 
Technology (CPTEn), School of Electrical and Computer Engineering (FEEC), 
University of Campinas (UNICAMP), under the supervision of 
**Prof. Dr. Marcos J. Rider Flores**.

It is associated with a planned research internship at the 
**University of Melbourne** under **Prof. Luis Ochoa**, supported by the 
FAPESP BEPE program.
