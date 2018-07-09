for i in ./*.krn; do
  BASE=`basename $i .krn`
  echo "Processing $BASE" >&2
  proof $BASE.krn | grep 'Error'
  hum2xml $BASE.krn > $BASE.xml
done
