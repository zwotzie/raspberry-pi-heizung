#!/bin/bash
# Auf dem Remote-Host ausführen

DB_HOST="db1234.db.xxx.com"
DB_USER="dein_user"
DB_NAME="heizung"
OUT_DIR="$HOME/heizung_export"

mkdir -p "$OUT_DIR"

# Passwort sicher abfragen
echo -n "MySQL Passwort: "
read -s DB_PASS
echo

for YEAR in $(seq 2015 2026); do
  echo "→ Exportiere Jahr $YEAR ..."

  mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" \
    --batch --raw --skip-column-names \
    -e "
      SELECT id, date,
             analog1, analog2, analog3, analog4, analog5, analog6,
             analog7, analog8, analog9, analog10, analog11, analog13,
             analog15, analog16,
             speed2, speed3, speed4,
             digital1, digital2, digital3, digital4, digital5,
             digital6, digital7, digital8, digital9, digital10, digital11
      FROM t_data
      WHERE frame = 'frame1'
        AND date >= '${YEAR}-01-01'
        AND date <  '$((YEAR+1))-01-01'
      ORDER BY id
    " | gzip > "$OUT_DIR/heizung-${YEAR}.csv.gz"

  echo "  → fertig: heizung-${YEAR}.csv.gz"
done

echo "Alle Jahre exportiert nach $OUT_DIR"
ls -lh "$OUT_DIR"