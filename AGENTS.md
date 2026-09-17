AGRICASCADE ENGINEERING RULES

1. Read the existing repository before changing code.

2. Do not invent duplicate schemas.

3. Canonical schemas live under agricascade/schemas/.

4. Business logic never belongs inside Streamlit UI code.

5. The core pipeline is:

   OBSERVE
   →
   INITIALIZE STATE
   →
   SIMULATE
   →
   PROPAGATE
   →
   DETECT BRANCH
   →
   TEST INTERVENTION
   →
   COUNTERFACTUAL

6. ML is used for estimation/forecasting only.

7. The cascade engine must remain deterministic for a fixed seed.

8. Every stochastic experiment requires an explicit random seed.

9. Never hard-code demo results.

10. Every UI number must come from the actual computational pipeline.

11. Synthetic values must be explicitly marked synthetic.

12. Real observations and synthetic scenario variables must remain distinguishable.

13. Never claim satellite data directly measures unobserved subsurface variables.

14. Never silently swallow exceptions.

15. Never use future data in temporal model features.

16. Never use random train/test splitting for temporal forecasting.

17. Every model output must expose uncertainty where applicable.

18. Every intervention must be re-simulated using the same cascade engine.

19. Never report an intervention as successful without checking
    the post-intervention trajectory.

20. Never calculate a benefit using hard-coded numbers.

21. Do not add an LLM to runtime.

22. Do not add authentication, payments, mobile apps, or cloud infrastructure.

23. Do not introduce a deep-learning model unless a baseline experiment
    demonstrates that simpler models are insufficient.

24. Do not introduce FNO/PINO/PDE solvers into the MVP.

25. Do not add a dependency unless it is necessary.

26. Document every scientific assumption.

27. Distinguish measured, estimated, simulated and assumed variables.

28. Keep the simulation model independently executable without Streamlit.

29. Tests must cover every core transition and intervention.

30. Before declaring completion:
    pytest
    end-to-end simulation
    deterministic scenario replay
    benchmark experiment

31. Do not describe an established modelling technique as novel.

32. If a feature does not strengthen cascade reconstruction,
    branch detection, counterfactual intervention, or validation,
    it is out of scope.