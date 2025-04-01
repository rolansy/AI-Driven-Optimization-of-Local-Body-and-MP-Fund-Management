// Market rates for different project types
const marketRates = {
    "Road Construction": 1000000,
    "School Building": 2000000,
    "Hospital Equipment": 1500000,
    "Water Supply": 800000,
    "Park Development": 500000
};

// Standard deviations for each project type (20% of market rate)
const standardDeviations = {};
for (let project in marketRates) {
    standardDeviations[project] = marketRates[project] * 0.20;
}

// Add jStat library for z-score calculation if it doesn't exist
if (typeof jStat === 'undefined') {
    // Simple implementation of z-score calculation
    const jStat = {
        zscore: function(x, mean, std) {
            return (x - mean) / std;
        }
    };
    window.jStat = jStat;
}

function detectCorruption(amount, project) {
    const marketRate = marketRates[project];
    const stdDev = standardDeviations[project];

    if (!marketRate) {
        console.error("Project type not found:", project);
        return {
            isCorrupt: false,
            marketRate: 0,
            zScore: 0,
            message: "Unknown project type"
        };
    }

    // Calculate z-score
    const zScore = (amount - marketRate) / stdDev;
    
    // Round z-score to 2 decimal places
    const roundedZScore = Math.round(zScore * 100) / 100;

    const result = {
        isCorrupt: false,
        marketRate: marketRate,
        zScore: roundedZScore,
        message: ""
    };

    if (Math.abs(zScore) > 2) {
        result.isCorrupt = true;
        if (amount > marketRate) {
            result.message = "Warning: Amount significantly higher than market rate!";
        } else {
            result.message = "Warning: Amount significantly lower than market rate!";
        }
    } else {
        result.message = "Transaction appears normal";
    }

    return result;
}