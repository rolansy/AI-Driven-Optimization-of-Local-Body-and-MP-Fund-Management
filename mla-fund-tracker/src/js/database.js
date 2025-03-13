class FundDatabase {
    constructor() {
        this.totalFund = 50000000; // Updated to 5 crore
        this.usedFund = 0;
        this.transactions = [];
        this.marketRates = {};
    }

    async loadMarketRates() {
        try {
            const response = await fetch('../data/market-rates.json');
            this.marketRates = await response.json();
        } catch (error) {
            console.error('Error loading market rates:', error);
        }
    }

    validateTransaction(amount, project) {
        const marketRate = this.marketRates[project] || 0;
        const threshold = marketRate * 1.2; // 20% threshold
        
        if (amount > threshold) {
            return {
                valid: false,
                message: `Suspicious transaction: Amount exceeds market rate by ${((amount - marketRate)/marketRate * 100).toFixed(2)}%`
            };
        }
        return { valid: true };
    }

    addTransaction(mlaName, amount, project) {
        const validation = this.validateTransaction(amount, project);
        if (!validation.valid) {
            return validation;
        }

        if (this.usedFund + amount > this.totalFund) {
            return {
                valid: false,
                message: "Insufficient funds"
            };
        }

        this.transactions.push({
            mlaName,
            amount,
            project,
            date: new Date()
        });
        this.usedFund += amount;
        return { valid: true };
    }

    getRemainingFund() {
        return this.totalFund - this.usedFund;
    }
}

const fundDB = new FundDatabase();
fundDB.loadMarketRates();