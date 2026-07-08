# global_leaks

**Категория:** iRidi Script
**Источник:** ticket 976-903287

---

Undeclared variables leak to global scope. Common: for-loop counters, 'self = this', temp vars. Found in ticket 976 across 6 scripts.