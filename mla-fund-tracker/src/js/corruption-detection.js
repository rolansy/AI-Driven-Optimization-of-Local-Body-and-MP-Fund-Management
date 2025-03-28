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

// Set placeholder for project input field
const validProjects = Object.keys(marketRates).join(", ");
document.getElementById('project').placeholder = `Enter one of: ${validProjects}`;

function detectCorruption(amount, project) {
    const marketRate = marketRates[project];
    const stdDev = standardDeviations[project];

    // Calculate z-score using jStat
    const zScore = jStat.zscore(amount, marketRate, stdDev);
    
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