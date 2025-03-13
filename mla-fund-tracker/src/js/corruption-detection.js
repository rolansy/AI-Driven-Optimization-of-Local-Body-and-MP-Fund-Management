const marketRates = {
    "Road Construction": 750000,
    "School Renovation": 180000,
    "Water Supply": 100000,
    "Street Lighting": 130000,
    "Park Development": 400000
};

function calculateZScore(amount, projectType) {
    const marketRate = marketRates[projectType];
    if (!marketRate) return null;

    const deviation = amount - marketRate;
    const threshold = marketRate * 0.2; // 20% as standard deviation
    return deviation / threshold;
}

function detectCorruption(amount, projectType) {
    const zScore = calculateZScore(amount, projectType);
    
    if (zScore === null) {
        return {
            isCorrupt: false,
            message: "Project type not found in reference data",
            zScore: 0,
            marketRate: 0
        };
    }

    if (Math.abs(zScore) > 2) {
        const percentageDeviation = ((amount - marketRates[projectType]) / marketRates[projectType] * 100).toFixed(2);
        return {
            isCorrupt: true,
            message: `WARNING: Amount deviates ${percentageDeviation}% from market rate`,
            zScore: zScore.toFixed(2),
            marketRate: marketRates[projectType]
        };
    }

    return {
        isCorrupt: false,
        message: "No abnormal deviation detected",
        zScore: zScore.toFixed(2),
        marketRate: marketRates[projectType]
    };
}