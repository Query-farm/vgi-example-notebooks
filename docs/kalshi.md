# Kalshi narrative plan

1. **How much depth is actually near the best quote?** Revise the existing recorded
   order-book analysis. Contrast the selected local band with the full book, keep
   YES/NO reciprocity explicit, and distinguish quoted quantity from executed trades.
2. **Which contracts belong to the same question?** Discover series, events and
   their markets; compare close times, statuses and contract thresholds. Use SQL
   joins to explain the hierarchy and prevent comparing unrelated contracts.
3. **Did trading move, or did the time bucket change?** Compare public trade prints
   with candlestick windows, volume and prices; make timestamps and aggregation
   intervals explicit. A bucket experiment should explain which summaries change.
4. **Where did the older market data go?** Read the archive cutoff, join settled
   markets to historical trades/candlesticks and preserve the difference between
   unavailable live rows and an actual absence of historical activity.

Build the visual and bootstrap standard on notebook 1 first, obtain reader feedback,
then apply it to the additional stories and other workers. Do not silently expand
this into trading recommendations, account access or order placement.
