Polymarket is a popular decentralized prediction market that allows users to bet on various predictions on things like weather, politics, cryptocurrencies and many other areas.

My Project focuses on the bitcoin price prediction market in 5-30 minute windows.(polymarket has 5min, 15min, 60min, 1 day windows so far)
Goal is simple, Predicting where the price will end up at the end compared to the beginning price of that particular window, Up or Down?

I spent a week looking at the BTC chart inorder to isolate the factors that affect BTC price, and realised there's one particular line of logic gap to take advantage of. and that gap won me around 65% win rate.
My algorithm takes advantage when the crypto market goes silent (Yes, the market moves fairly slow at particular time intervals throughout the day when big US and Asian institutes are asleep.)
I connect to the fastest BTC chart api(Binance live chart) and my algorithm calculates 3 parameters based on which the trade will be made.
Parameters:-
  1. Scan the order book for around 100 immediate pending orders and breaks them down into a weighted average that lies in (-1,1) interval, -1 implying huge sell orders incoming and +1 for buy orders.
  2. From the same order book list, look for huge chunk of orders around the close neighbourhood of the real time price, these huge chunks will eat the flow direction of the market incase heavy number of opposite orders arrive.(essentially a fool proof logic for a unique case in the 1st parameter, where the price doesn't move even though huge orders are placed)
  3. There are 2 phenomenon that can't be covered by previous 2 parameters. 
       1. Spoofing happens in HFT markets where orders are placed and removed quickly to throw off poorly coded Bots.
       2. Big whales place ghost orders that sit at a particular price in huge chunks, a trick to counter our 2nd parameter.
     
      Both of these can be countered easily by looking at the real-time market orders in a surrounding of our choice.

Based on these parameters the bot assesses the market speed, volatility and volume of trades and takes advantage on the Polymarket trade.
Though it absolutely gets wrecked in the high volatility periods, I believe its borderline insane for an individual to compete against insituitional algorithms and run away with any meaningful profit.(there have been exceptions but not in current times.) 
Go through the code for exact math used on 3 parameters :)

##Current work in progress: full automation and deploy into market. 
