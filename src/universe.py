"""Stock universe definitions for each market."""

import requests
import pandas as pd

# Chilean IPSA index (~30 largest companies on Bolsa de Santiago)
CHILE_TICKERS: list[str] = [
    "SQM-B.SN", "CMPC.SN", "FALABELLA.SN", "COPEC.SN", "BSANTANDER.SN",
    "BCI.SN", "ENELAM.SN", "CENCOSUD.SN", "CCU.SN", "ENELCHILE.SN",
    "CHILE.SN", "COLBUN.SN", "ITAUCL.SN", "RIPLEY.SN", "PARAUCO.SN",
    "AGUAS-A.SN", "SECURITY.SN", "BICE.SN", "SONDA.SN", "LTM.SN",
    "CONCHA.SN", "SALFACORP.SN", "CAP.SN", "FORUS.SN", "ECL.SN",
    "VAPORES.SN", "ANTARCHILE.SN", "BESALCO.SN", "NUEVAPOLAR.SN", "SMU.SN",
]

# Representative European stocks from STOXX 600 — major caps across key countries
EUROPE_TICKERS: list[str] = [
    # France (.PA)
    "MC.PA", "OR.PA", "TTE.PA", "SAN.PA", "AIR.PA", "BNP.PA", "DG.PA",
    "CS.PA", "RI.PA", "AI.PA", "SGO.PA", "EL.PA", "VIE.PA", "KER.PA",
    "LR.PA", "ATO.PA", "DSY.PA", "STM.PA", "HO.PA", "CAP.PA",
    # Germany (.DE)
    "SAP.DE", "ALV.DE", "SIE.DE", "DTE.DE", "BAYN.DE", "BAS.DE",
    "MRK.DE", "BMW.DE", "VOW3.DE", "RWE.DE", "DB1.DE", "HEI.DE",
    "IFX.DE", "MBG.DE", "ADS.DE", "DHER.DE", "SHL.DE", "ZAL.DE",
    # Spain (.MC)
    "ITX.MC", "SAN.MC", "IBE.MC", "BBVA.MC", "TEF.MC", "REP.MC",
    "CABK.MC", "FER.MC", "ENG.MC", "MAP.MC",
    # UK (.L)
    "SHEL.L", "AZN.L", "HSBA.L", "ULVR.L", "BP.L", "RIO.L", "GSK.L",
    "BATS.L", "REL.L", "NG.L", "LLOY.L", "BARC.L", "PRU.L", "DGE.L",
    "CPG.L", "VOD.L", "EXPN.L", "FLTR.L",
    # Italy (.MI)
    "ENEL.MI", "ISP.MI", "UCG.MI", "ENI.MI", "TIT.MI", "LDO.MI",
    "STM.MI", "MB.MI", "G.MI", "PRY.MI",
    # Netherlands (.AS)
    "ASML.AS", "HEIA.AS", "PHIA.AS", "REN.AS", "WKL.AS", "INGA.AS",
    "NN.AS", "AKZA.AS", "UMG.AS", "ABN.AS",
    # Switzerland (.SW)
    "NESN.SW", "ROG.SW", "NOVN.SW", "ABBN.SW", "ZURN.SW", "UBSG.SW",
    "CFR.SW", "SREN.SW", "LONN.SW", "GEBN.SW",
    # Sweden (.ST)
    "VOLV-B.ST", "ERIC-B.ST", "SAND.ST", "INVE-B.ST", "ATCO-A.ST",
    "EVO.ST", "ESSITY-B.ST", "SEB-A.ST", "SWED-A.ST", "HM-B.ST",
]


def get_sp500_tickers() -> list[str]:
    """Fetch current S&P 500 tickers from Wikipedia."""
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(url)
        df = tables[0]
        tickers = df["Symbol"].str.replace(".", "-", regex=False).tolist()
        return tickers
    except Exception as e:
        print(f"[universe] Warning: could not fetch S&P 500 list ({e}). Using fallback.")
        return _SP500_FALLBACK


# Fallback list with major S&P 500 components if Wikipedia is unavailable
_SP500_FALLBACK: list[str] = [
    "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "TSLA", "BERKB",
    "UNH", "XOM", "JNJ", "JPM", "V", "PG", "MA", "HD", "CVX", "MRK",
    "ABBV", "LLY", "AVGO", "PEP", "KO", "COST", "TMO", "MCD", "ACN",
    "WMT", "BAC", "CSCO", "CRM", "ABT", "DHR", "NEE", "ADBE", "TXN",
    "VZ", "PM", "NKE", "CMCSA", "RTX", "ORCL", "QCOM", "LOW", "AMGN",
    "HON", "UPS", "IBM", "CAT", "GS", "SBUX", "SPGI", "DE", "BA",
    "BLK", "AXP", "PLD", "GILD", "LMT", "MMC", "SYK", "MDLZ", "TGT",
    "ADI", "ISRG", "VRTX", "REGN", "ZTS", "CB", "MO", "SO", "DUK",
    "CL", "BDX", "EW", "EQIX", "PNC", "TFC", "USB", "WFC", "C",
    "INTC", "AMD", "MU", "AMAT", "LRCX", "KLAC", "MRVL", "PANW",
    "SNOW", "NOW", "WDAY", "TEAM", "ZM", "OKTA", "DDOG", "CRWD",
    "F", "GM", "TM", "HMC", "STLA", "CMG", "YUM", "DPZ", "QSR",
    "DIS", "NFLX", "T", "CHTR", "TMUS", "WBD", "FOX", "PARA",
    "CVS", "CI", "HUM", "ELV", "CNC", "MOH", "HCA", "UHS",
    "PFE", "BMY", "AMGN", "BIIB", "MRNA", "BNTX", "REGN", "VRTX",
    "XOM", "CVX", "COP", "SLB", "EOG", "PXD", "MPC", "VLO", "PSX",
    "APD", "LIN", "SHW", "ECL", "IFF", "EMN", "CE", "LYB", "DOW",
    "GE", "ETN", "EMR", "PH", "ROK", "AME", "FTV", "SWK", "IR",
    "SPG", "O", "AVB", "EQR", "DRE", "VTR", "WELL", "ARE", "CBRE",
    "GPN", "FIS", "FISV", "MA", "V", "AXP", "COF", "DFS", "SYF",
    "AIG", "MET", "PRU", "ALL", "TRV", "PGR", "HIG", "AFL", "GL",
    "AMT", "CCI", "SBAC", "VICI", "WY", "PLD", "PSA", "EXR", "CUBE",
    "WM", "RSG", "RNG", "EXPD", "JBHT", "CHRW", "XPO", "SAIA",
    "MMM", "DOV", "XYL", "WTS", "RXO", "GXO", "CARR", "OTIS",
    "NUE", "STLD", "RS", "CMC", "ATI", "AA", "FCX", "NEM", "AEM",
    "AMP", "TROW", "BEN", "IVZ", "NTRS", "STT", "BK", "SCHW",
]
