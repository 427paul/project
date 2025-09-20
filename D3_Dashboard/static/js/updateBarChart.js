function updateBarChart(group, color, datasetBarChart){
    const currentBarChart= get_percentage(group, datasetBarChart); 
   // bar chart와 동일하게 스케일 정의
    const xScale= d3.scaleLinear() 
        .domain([0, currentBarChart.length]) 
        .range([0, width]); 

    const yScale= d3.scaleLinear() 
        .domain([0, d3.max(currentBarChart, function(d) { return d.value; })]) 
        .range([height,0]); 

   const bar = d3.select('#barChartsvg'); 
    bar.selectAll("text.title") 
        .attr("x", (width + margin.left+ margin.right)/2) 
        .attr("y", graph_misc.title) 
        .attr("class","title") 
        .attr("text-anchor", "middle") 
        .text("Tenure group for churned customers "+group);

    const visualization = d3.select('barChartPlot') 
        .datum(currentBarChart); // 여러 SVG 요소에 데이터 바인딩

    visualization.selectAll('rect') 
        .data(currentBarChart) 
        .transition() .duration(750) 
        .attr('x', (width + margin.left+ margin.right)/2) 
        .attr('y', graph_misc.title) 
        .attr('class', 'title') 
        .attr('text-anchor', 'middle') 
        .text('Tenure group for churned customers '+group); 

    const plot = d3.select('#barChartPlot') 
        .datum(currentBarChart);

    plot.selectAll('rect') 
        .data(currentBarChart) .transition() 
        .duration(800) 
        .attr('x', function(d,i){ return xScale(i); }) 
        .attr('width', width/currentBarChart.length-barPadding) 
        .attr('y', function(d){ return yScale(d.value) }) 
        .attr("height", function(d) { return height-yScale(d.value); }) 
        .attr("fill", color);

    plot.selectAll("text.yAxis") 
        .data(currentBarChart) 
        .transition() 
        .duration(750) 
        .attr("text-anchor", "middle") 
        .attr("x", function(d, i) { return(i * (width / currentBarChart.length)) + ((width / currentBarChart.length-barPadding) / 2);}) 
        .attr("y", function(d) { return yScale(d.value) -graph_misc.ylabel;}) 
        .text(function(d) { return d.value+'%';}) 
        .attr("class", "yAxis"); 
};