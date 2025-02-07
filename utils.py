def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:  # Untuk angka 11-20 (pengecualian aturan umum)
        suffix = "th"
    else:
        suffixes = {1: "st", 2: "nd", 3: "rd"}
        suffix = suffixes.get(n % 10, "th")  # Default ke "th" jika tidak termasuk 1, 2, atau 3

    return f"{n}{suffix}"


def plural_number(number, prefix=""):
  if number == 1:
    return f"{number} {prefix}"
  else:
    return f"{number} {prefix}s"