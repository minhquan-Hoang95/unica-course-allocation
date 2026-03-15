## Student Preference Normalization

Student preferences over courses are expressed as rankings of courses using a normalized system.

### Mid-rank method

Preferences are normalized using the **mid-rank/average rank for ties method**.  
When multiple courses have the same preference level, their rank is the average of the positions they occupy.

Example:

| Course | Rank |
|------|------|
| A | 1 |
| B | 2 |
| C | 3.5 |
| D | 3.5 |

In this example, courses **C** and **D** are ranked for positions **3 and 4**.
Instead of assigning ranks 3 and 4, both courses receive the **average rank**:

(3 + 4) / 2 = **3.5**

This method keeps a **constant sum** when ranking a fixed number of courses :

sum of ranks = M(M + 1) / 2

where **M** is the total number of courses.

This property ensures that rankings remain **consistent and comparable across students**.

### Mandatory courses

Mandatory courses must always appear **before optional courses** in a student's ranking.

During preference generation:
- mandatory courses are assigned the **highest priority**
- optional courses are ranked after them

This guarantees that mandatory courses always receive **better ranks than optional courses**.

---

## Generate student preferences

To generate synthetic student preference data, run:

```
python syntheticStudentGenerator.py
```

This will generate the file:

studentsRandom.csv