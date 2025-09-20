function d3PieChart(dataset, datasetBarChart){ 
    // SVG의 크기와 속성 설정
    const margin = {top:20, right:20, bottom:20, left:20}; 
    const width = 350- margin.left- margin.right, 
    height = 350- margin.top- margin.bottom, 
    outerRadius = Math.min(width, height) / 2, 
    innerRadius = outerRadius * .5, 
    color = d3.scaleOrdinal(d3.schemeAccent); 
    // index.html 템플릿 파일에서 id가 pieChart인 div 선택
    const visualization = d3.select('#pieChart')
        .append("svg") // SVG 요소 삽입
        .data([dataset]) //파이 차트 데이터 바인딩
        .attr("width", width) 
        .attr("height", height) 
        .append("g") //SVG 구성 요소 그룹화
        .attr("transform", "translate(" + outerRadius + "," + outerRadius + ")"); //페이지 로딩 시 파이 차트 변환 적용
    const data = d3.pie() // 파이 차트의 다양한 세그먼트를 개발하기 위한 데이터 객체 생성
        .sort(null) 
        .value(function(d){return d.value;})(dataset); 
    // Flask 앱에서 파이 차트 데이터 값을 가져옴, 이때 파이 차트는 JSON 객체의 'value' 키와 연결됨
    // 외부 원형 차트를 생성하는 호(arc) 생성기 만들기
    const arc = d3.arc() 
        .outerRadius(outerRadius) 
        .innerRadius(0); 
    // 내부 원형 차트를 생성하는 호(arc) 생성기 만들기
    const innerArc= d3.arc() 
        .innerRadius(innerRadius) 
        .outerRadius(outerRadius);
    // 생성된 데이터 객체를 기반으로 파이 차트 조각 생성
    const arcs = visualization.selectAll("g.slice") 
        .data(data) 
        .enter() // 요소에 데이터의 초기 결합 생성
        .append("svg:g") 
        .attr("class", "slice") 
        .on("click", click);
    arcs.append("svg:path") // path 요소 생성
        .attr("fill", function(d, i) { return color(i); } ) // 색상 추가
        .attr("d", arc) // arc 그리기 함수를 사용하여 실제 SVG 경로 생성
        .append("svg:title") // 각 파이 차트 조각에 제목 추가
        .text(function(d) { return d.data.category+ ": " + 
        d.data.value+"%"; }); 
    d3.selectAll("g.slice") // 그룹화된 SVG 요소(piechart)에서 조각 선택
        .selectAll("path") 
        .transition() // 로딩 시 파이 차트 트랜지션 설정
        .duration(200) 
        .delay(5) 
        .attr("d", innerArc);
    arcs.filter(function(d) { return d.endAngle-d.startAngle> .1; }) // 특정 각도에서 조각 레이블 정의
        .append("svg:text") // SVG에 텍스트 영역 삽입
        .attr("dy", "0.20em") // 텍스트 내용의 위치를 y축을 따라 이동
        .attr("text-anchor", "middle") // 조각 레이블 위치 설정
        .attr("transform", function(d) { return"translate("+ innerArc.centroid(d) + ")"; }) // 트랜지션과 변환 시 위치 조정
        .text(function(d) { return d.data.category; }); // 조각에 카테고리 이름 추가
    visualization.append("svg:text") // 파이 차트 중앙에 차트 제목 추가
        .attr("dy", ".20em") 
        .attr("text-anchor", "middle") 
        .text("churned customers") 
        .attr("class","title"); 
        // 파이 차트 조각을 클릭할 때 막대 차트를 업데이트하는 함수
        function click(d, i) { 
        updateBarChart(d.data.category, color(i), datasetBarChart); 
        } 
        }
