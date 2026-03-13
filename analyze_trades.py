import pandas as pd
import numpy as np

def analyze_backtest():
    try:
        df = pd.read_csv("backtest_trades.csv")
    except:
        print("Could not find backtest_trades.csv")
        return

    # Convert PnL to numeric just in case
    df['pnl_plus_fees'] = df['pnl'] 
    
    # 1. Overall Summary
    total_trades = len(df)
    winners = df[df['pnl'] > 0]
    losers = df[df['pnl'] <= 0]
    win_rate = (len(winners) / total_trades) * 100
    
    total_pnl = df['pnl'].sum()
    profit_factor = abs(winners['pnl'].sum() / losers['pnl'].sum()) if len(losers) > 0 else float('inf')
    
    # 2. Symbol Breakdown
    symbol_summary = []
    for symbol in df['symbol'].unique():
        s_df = df[df['symbol'] == symbol]
        s_win_rate = (len(s_df[s_df['pnl'] > 0]) / len(s_df)) * 100
        s_pnl = s_df['pnl'].sum()
        symbol_summary.append({
            'Symbol': symbol,
            'Trades': len(s_df),
            'Win Rate': f"{s_win_rate:.2f}%",
            'Total PnL': f"{s_pnl:.2f} USDT"
        })

    # 3. Best and Worst Trades
    best_trade = df.loc[df['pnl'].idxmax()]
    worst_trade = df.loc[df['pnl'].idxmin()]

    # 4. Average Metrics
    avg_win = winners['pnl'].mean()
    avg_loss = losers['pnl'].mean()
    
    # Print results in a structured ways
    print("## Detailed Analysis Results")
    print(f"- **Total Trades**: {total_trades}")
    print(f"- **Final Net PnL**: {total_pnl:.2f} USDT")
    print(f"- **Overall Win Rate**: {win_rate:.2f}%")
    print(f"- **Profit Factor**: {profit_factor:.2f}")
    print(f"- **Average Win**: {avg_win:.2f} USDT")
    print(f"- **Average Loss**: {avg_loss:.2f} USDT")
    print("\n### 🌐 Performance by Symbol")
    print("| Symbol | Trades | Win Rate | Net PnL |")
    print("| :--- | :--- | :--- | :--- |")
    for s in symbol_summary:
        print(f"| {s['Symbol']} | {s['Trades']} | {s['Win Rate']} | {s['Total PnL']} |")
    
    print("\n### 🏆 Top 5 Wins")
    top_5 = df.sort_values(by='pnl', ascending=False).head(5)
    print("| Symbol | Side | PnL Net | Reason |")
    print("| :--- | :--- | :--- | :--- |")
    for _, r in top_5.iterrows():
        print(f"| {r['symbol']} | {r['side']} | {r['pnl']:.2f} | {r['reason']} |")

    print("\n### 📉 Top 5 Losses")
    worst_5 = df.sort_values(by='pnl', ascending=True).head(5)
    print("| Symbol | Side | PnL Net | Reason |")
    print("| :--- | :--- | :--- | :--- |")
    for _, r in worst_5.iterrows():
        print(f"| {r['symbol']} | {r['side']} | {r['pnl']:.2f} | {r['reason']} |")

if __name__ == "__main__":
    analyze_backtest()
