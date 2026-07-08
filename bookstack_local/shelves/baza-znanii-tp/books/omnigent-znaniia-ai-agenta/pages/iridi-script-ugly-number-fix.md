# ugly_number_fix

**Категория:** iRidi Script
**Источник:** built-in constraint

---

parseFloat with || default value is buggy when value is 0 (treated as falsy). Use isNaN() check instead. For floating-point artifacts (0.30000000000000004) use toFixed(n) or string match.