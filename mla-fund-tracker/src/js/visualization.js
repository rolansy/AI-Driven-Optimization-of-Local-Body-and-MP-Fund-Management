function updateVisualization() {
    const width = 600;
    const height = 400;
    const radius = Math.min(width, height) / 2;
    
    // Clear previous visualization
    d3.select("#fundChart").selectAll("*").remove();
    
    const svg = d3.select("#fundChart")
        .append("svg")
        .attr("width", width)
        .attr("height", height)
        .append("g")
        .attr("transform", `translate(${width/2}, ${height/2})`);

    // Data preparation
    const usedAmount = fundDB.getUsedAmount();
    const availableAmount = fundDB.getAvailableAmount();
    
    const data = [
        { label: "Used Fund", value: usedAmount, color: "#FF0000" },    // Bright red
        { label: "Available Fund", value: availableAmount, color: "#2ECC40" }  // Green
    ];

    // Create pie chart
    const pie = d3.pie()
        .sort(null)
        .value(d => d.value);

    const arc = d3.arc()
        .innerRadius(0)
        .outerRadius(radius - 40);

    // Add slices with explicit colors
    const slices = svg.selectAll("path")
        .data(pie(data))
        .enter()
        .append("path")
        .attr("d", arc)
        .attr("fill", d => d.data.color)  // Use explicit colors from data
        .attr("stroke", "white")
        .style("stroke-width", "2px");

    // Add percentage labels
    const labels = svg.selectAll("text")
        .data(pie(data))
        .enter()
        .append("text")
        .attr("transform", d => `translate(${arc.centroid(d)})`)
        .attr("dy", "0.35em")
        .attr("text-anchor", "middle")
        .attr("fill", "white")
        .style("font-size", "16px")
        .style("font-weight", "bold")
        .text(d => {
            const percentage = ((d.data.value / fundDB.totalFund) * 100).toFixed(1);
            return `${percentage}%`;
        });

    // Add legend
    const legend = svg.selectAll(".legend")
        .data(data)
        .enter()
        .append("g")
        .attr("class", "legend")
        .attr("transform", (d, i) => `translate(-50,${i * 20 - radius + 20})`);

    legend.append("rect")
        .attr("x", 0)
        .attr("width", 18)
        .attr("height", 18)
        .attr("fill", d => d.color);

    legend.append("text")
        .attr("x", 24)
        .attr("y", 9)
        .attr("dy", ".35em")
        .text(d => `${d.label}: ₹${d.value.toLocaleString()}`);
}