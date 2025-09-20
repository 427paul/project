// SVG의 크기와 속성 설정 
const margin = {top: 20, right: 10, bottom: 20, left: 20},
width = 350- margin.left- margin.right, 
height = 350- margin.top- margin.bottom, 
barPadding = 5, 
graph_misc = {ylabel: 4, xlabelH : 5, title:9};
 // 기본 그룹 설정 
const group = "All"; 
// 전체 데이터 세트에서 특정 선택된 그룹의 백분율 값을 가져오는 함수 
function get_percentage(group, datasetBarChart){ 
const _ = []; 
for (instance in datasetBarChart){ 
if (datasetBarChart[instance].group==group){ 
_.push(datasetBarChart[instance]) 
}
 } return _;
 };

 function d3BarChart(datasetBarChart){ 
    defaultBarChart= get_percentage(group, datasetBarChart);
     const xScale= d3.scaleLinear()
     .domain([0, defaultBarChart.length]) // 데이터 객체의 길이를 기준으로 스케일 범위 설정
    .range([0, width]); 
    const yScale= d3.scaleLinear() // Barcharty axis scale 
    .domain([0, d3.max(defaultBarChart, function(d) { return d.value; })]) //데이터 최대 값을 기준으로 스케일 설정
    .range([height, 0]); // index.html 템플릿 파일에서 id가 barChart인 div 선택
    const bar = d3.select('#barChart') 
    .append('svg') 
    .attr('width', width + margin.left+ margin.right) 
    .attr('height', height + margin.top+ margin.bottom) 
    .attr('id', 'barChartPlot'); 
     // 제목 추가
    bar.append('text') 
    .attr('x', (width + margin.left + margin.right)/2) 
    .attr('y', graph_misc.title) 
    .attr('class','title') 
    .attr('text-anchor', 'middle') 
    .text('Tenure group for churned customers');
    const visualization = bar.append('g') 
    .attr("transform", "translate(" + margin.left + "," + (margin.top + graph_misc.ylabel) + ")"); 
    visualization.selectAll("rect") 
    .data(defaultBarChart) 
    .enter() 
    .append("rect") 
    .attr("x", function(d, i) { return xScale(i); }) 
    .attr("width", width / defaultBarChart.length- barPadding) 
    .attr("y", function(d) { return yScale(d.value); }) 
    .attr("height", function(d) { return height-yScale(d.value); }) 
    .attr("fill", "#757077");

        // 레이블 추가
    visualization.selectAll('text') 
    .data(defaultBarChart) 
    .enter() 
    .append("text") 
    .text(function(d) { return d.value+"%"; }) 
    .attr("text-anchor", "middle") 
    .attr("x", function(d, i) { return (i * (width / defaultBarChart.length)) + ((width / defaultBarChart.length-
    barPadding) / 2); }) 
    .attr("y", function(d) { return (yScale(d.value) - graph_misc.ylabel) })//Y 축을 JSON 데이터에서 제공된 값으로 설정
    .attr("class", "yAxis"); 
    const xLabels = bar 
    .append("g") 
    .attr("transform", "translate(" + margin.left + "," + (margin.top + height + graph_misc.xlabelH) + ")"); 
    xLabels.selectAll("text.xAxis") 
    .data(defaultBarChart) 
    .enter() 
    .append("text") 
    .text(function(d) { return d.category;}) 
    .attr("text-anchor", "middle") 
    .attr("x", function(d, i) { return (i * (width / defaultBarChart.length)) + ((width / defaultBarChart.length-
    barPadding) / 2); }) 
    .attr("y", 15) 
    .attr("class", "xAxis"); 
    }