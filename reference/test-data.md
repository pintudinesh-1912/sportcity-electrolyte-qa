# Test Data Reference

These records exist in the environment. Use them as the inputs for your testing.
Members exist in Perfect Gym (PG) with different membership states; the Perfect
Gym screenshots and DataDog snippets provided for Part 2 reflect the same data.

## Business rules (recap)

- A member can **freeze** their membership (e.g. injury or travel). While
  frozen, they **cannot book** classes.
- There are two standard plans: **City One** (single club) and **City Plus**
  (all clubs). **City Plus costs a few euros more** than City One.
- Discounted plans, such as **City Student**, are priced lower by design and are
  not part of that comparison.
- The spots shown for a class must reflect the true capacity in Perfect Gym.

## Auth

All requests require the header:

```
X-Api-Key: sportcity-test-key
```

## Members

| Member ID | Name          | Membership                               |
|-----------|---------------|------------------------------------------|
| M-1001    | Anna de Vries | City Plus — active                       |
| M-1002    | Tom Bakker    | City One — frozen (injury/travel)        |
| M-1003    | Lisa Jansen   | City One — expired                       |
| M-1004    | Sara Visser   | Prospect — used to purchase a membership |

(Plus any member ID not in this list, e.g. `M-9999`, represents a member that
does not exist.)

## Plans

| Plan ID      | Name         | Category   | Coverage                                  |
|--------------|--------------|------------|-------------------------------------------|
| CITY-ONE     | City One     | Standard   | Single club (lower standard price)        |
| CITY-PLUS    | City Plus    | Standard   | All clubs (higher standard price)         |
| CITY-STUDENT | City Student | Discounted | Single club, for students (discounted)    |

## Group classes

| Class ID | Name         | Scheduled (local, Europe/Amsterdam) |
|----------|--------------|-------------------------------------|
| C-2001   | Spinning     | 2027-06-21 18:00                    |
| C-2002   | Yoga         | 2027-06-22 09:00                    |
| C-2003   | BodyPump     | 2027-06-23 19:30                    |
| C-2004   | HIIT Express | 2027-06-24 07:00                    |
| C-2005   | Pilates      | 2027-11-15 18:00                    |

## Example requests

```bash
# List classes
curl -H "X-Api-Key: sportcity-test-key" http://localhost:3000/v1/classes

# List plans and prices
curl -H "X-Api-Key: sportcity-test-key" http://localhost:3000/v1/plans

# Get a member
curl -H "X-Api-Key: sportcity-test-key" http://localhost:3000/v1/members/M-1001

# Purchase a membership
curl -H "X-Api-Key: sportcity-test-key" -H "Content-Type: application/json" \
  -X POST http://localhost:3000/v1/memberships \
  -d '{"memberId":"M-1004","planId":"CITY-ONE"}'

# Book a class
curl -H "X-Api-Key: sportcity-test-key" -H "Content-Type: application/json" \
  -X POST http://localhost:3000/v1/bookings \
  -d '{"memberId":"M-1001","classId":"C-2001"}'
```
